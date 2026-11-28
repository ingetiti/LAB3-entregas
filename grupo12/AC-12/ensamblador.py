import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


OPCODES = {
	"BR": 0b00000,
	"ADD": 0b00001,
	"LD": 0b00010,
	"ST": 0b00011,
	"JSR": 0b00100,
	"AND": 0b00101,
	"LDR": 0b00110,
	"STR": 0b00111,
	"LDB": 0b10101,
	"STB": 0b10110,
	"LDH": 0b10111,
	"STH": 0b11000,
	"RTI": 0b01000,
	"NOT": 0b01001,
	"JMP": 0b01100,
	"LEA": 0b01110,
	"TRAP": 0b01111,
	"LSHF": 0b01101,
	"RSHFL": 0b10000,
	"RSHFA": 0b10001,
	"ADDI5": 0b11001,
	"LDRX": 0b11010,
	"STRX": 0b11011,
	"MUL": 0b01010,
	"MULH": 0b01011,
	"SUB": 0b11100,
}
BRANCH_CONDITIONS = {
	"BR": 0b111,
	"BRN": 0b100,
	"BRZ": 0b010,
	"BRP": 0b001,
	"BRNZ": 0b110,
	"BRNP": 0b101,
	"BRZP": 0b011,
	"BRNZP": 0b111,
}
BRANCH_FLAGS = {
	"BRV": 0b10011,
	"BRC": 0b10100,
}
TRAP_VECTORS = {
	"GETC": 0x20,
	"OUT": 0x21,
	"PUTS": 0x22,
	"IN": 0x23,
	"PUTSP": 0x24,
	"HALT": 0x25,
}
DIRECTIVES = {".ORIG", ".END", ".FILL", ".BLKW", ".BYTE", ".STRINGZ", ".EXTERNAL"}
PSEUDO_OPS = {"JSRR", "RET", "HALT", "GETC", "OUT", "PUTS", "IN", "PUTSP"}
SOURCE_FILE_SUFFIXES = {".asm", ".txt"}



@dataclass
class SourceLine:
	number: int
	address: int
	operation: str
	operands: list[str]


class AssemblyError(Exception):
	def __init__(self, diagnostics):
		self.diagnostics = diagnostics
		super().__init__("\n".join(
			f"línea {line}: {message}" for line, message in diagnostics
		))


class LC3Assembler:
	def __init__(self):
		self.labels = {}
		self.last_format = None
		self.last_listing = []

	def assemble(self, source, fractional_bits=0, source_path=None):
		self.last_listing = []
		if not 0 <= fractional_bits <= 15:
			raise ValueError("la cantidad de bits fraccionarios debe estar entre 0 y 15")
		self.fractional_bits = fractional_bits
		source = self._expand_external(source, source_path)
		source_format = self.detect_format(source)
		self.last_format = source_format
		if source_format != "ASM":
			origin, words = self._assemble_machine_code(source, source_format)
			self.last_listing = [
				(origin + index * 2, word, "Código máquina")
				for index, word in enumerate(words)
			]
			return origin, words

		records, origin, errors = self._first_pass(source)
		byte_image = bytearray()
		listing_by_address = {}

		for record in records:
			try:
				encoded = self._encode(record)
			except ValueError as error:
				errors.append((record.number, str(error)))
				continue

			offset = record.address - origin
			while len(byte_image) < offset:
				padding_address = origin + len(byte_image)
				byte_image.append(0)
				self._add_listing_description(
					listing_by_address,
					padding_address & ~1,
					"alineación",
				)

			instruction = self._listing_instruction(record)
			if record.operation == ".BYTE":
				for index, value in enumerate(encoded):
					address = record.address + index
					byte_image.append(value & 0xFF)
					self._add_listing_description(
						listing_by_address,
						address & ~1,
						instruction,
					)
			else:
				encoded_words = encoded if isinstance(encoded, list) else [encoded]
				for index, word in enumerate(encoded_words):
					address = record.address + index * 2
					byte_image.extend((word & 0xFF, (word >> 8) & 0xFF))
					self._add_listing_description(
						listing_by_address,
						address,
						instruction,
					)

		if errors:
			raise AssemblyError(errors)
		if len(byte_image) & 1:
			padding_address = origin + len(byte_image)
			byte_image.append(0)
			self._add_listing_description(
				listing_by_address,
				padding_address & ~1,
				"alineación",
			)
		words = [
			byte_image[index] | (byte_image[index + 1] << 8)
			for index in range(0, len(byte_image), 2)
		]
		self.last_listing = [
			(
				origin + index * 2,
				word,
				listing_by_address.get(origin + index * 2, "Datos"),
			)
			for index, word in enumerate(words)
		]
		return origin, words

	@staticmethod
	def _add_listing_description(listing_by_address, address, description):
		existing = listing_by_address.get(address)
		if existing is None:
			listing_by_address[address] = description
		elif description not in existing.split(" | "):
			listing_by_address[address] = f"{existing} | {description}"

	@staticmethod
	def _strip_comment(line):
		in_quotes = False
		escaped = False
		for index, char in enumerate(line):
			if in_quotes:
				if escaped:
					escaped = False
				elif char == "\\":
					escaped = True
				elif char == '"':
					in_quotes = False
			else:
				if char == ";":
					return line[:index]
				if char == '"':
					in_quotes = True
		return line

	@staticmethod
	def _split_comment(line):
		code = LC3Assembler._strip_comment(line)
		if len(code) < len(line):
			return code, ";", line[len(code) + 1:]
		return code, "", ""

	@staticmethod
	def _parse_stringz(raw_operand):
		text = raw_operand.strip()
		if not text or not text.startswith('"'):
			raise ValueError('.STRINGZ requiere una cadena entre comillas dobles ("...")')

		escapes = {
			"n": "\n",
			"t": "\t",
			"r": "\r",
			"0": "\0",
			'"': '"',
			"\\": "\\",
		}
		characters = []
		index = 1
		closed = False
		while index < len(text):
			char = text[index]
			if char == '"':
				if index != len(text) - 1:
					raise ValueError(".STRINGZ solo acepta una cadena entre comillas dobles")
				closed = True
				break
			if char == "\\":
				index += 1
				if index >= len(text):
					raise ValueError("secuencia de escape incompleta en .STRINGZ")
				escape_char = text[index]
				if escape_char not in escapes:
					raise ValueError(f"secuencia de escape no soportada en .STRINGZ: \\{escape_char}")
				char = escapes[escape_char]
			if ord(char) > 0xFF:
				raise ValueError(f"carácter fuera de rango de 8 bits en .STRINGZ: {char!r}")
			characters.append(char)
			index += 1

		if not closed:
			raise ValueError("cadena sin cerrar en .STRINGZ")
		return "".join(characters)

	def _expand_external(self, source, source_path):
		has_external = any(
			re.match(r"\s*\.EXTERNAL(?:\s|$)", self._strip_comment(line), re.IGNORECASE)
			for line in source.splitlines()
		)
		if not has_external:
			return source
		if source_path is None:
			raise AssemblyError([(1, ".EXTERNAL requiere un archivo fuente .asm o .txt")])

		root_path = Path(source_path).resolve()
		if root_path.suffix.lower() not in SOURCE_FILE_SUFFIXES:
			raise AssemblyError([(1, "el archivo que usa .EXTERNAL debe tener extensión .asm o .txt")])

		allowed_roots = {
			root_path.parent.resolve(),
			(root_path.parent / "lib").resolve(),
		}
		external_pattern = re.compile(
			r'\.EXTERNAL\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s,]+))\s*',
			re.IGNORECASE,
		)
		modules = {}
		module_order = []
		errors = []

		def source_lines(module_source):
			for line_number, original in enumerate(module_source.splitlines(), start=1):
				code = self._strip_comment(original).strip()
				first_token = code.split(None, 1)[0].upper() if code else ""
				yield line_number, original, code, first_token

		def resolve_external(filename, current_path):
			external_path = Path(filename)
			if (
				external_path.is_absolute()
				or "/" in filename
				or "\\" in filename
				or external_path.name != filename
			):
				raise ValueError(".EXTERNAL solo puede indicar un archivo del proyecto")

			suffix = external_path.suffix.lower()
			if suffix and suffix not in SOURCE_FILE_SUFFIXES:
				raise ValueError(
					"el archivo indicado por .EXTERNAL debe tener extensión .asm o .txt"
				)
			suffixes = (suffix,) if suffix else (".asm", ".txt")
			search_directories = []
			for directory in (
				current_path.parent,
				root_path.parent / "lib",
				root_path.parent,
			):
				resolved_directory = directory.resolve()
				if (
					resolved_directory in allowed_roots
					and directory.is_dir()
					and resolved_directory not in search_directories
				):
					search_directories.append(resolved_directory)

			expected_names = {
				external_path.with_suffix(candidate_suffix).name.lower()
				for candidate_suffix in suffixes
			}
			candidates = []
			for directory in search_directories:
				for path in directory.iterdir():
					if path.is_file() and path.name.lower() in expected_names:
						candidates.append(path.resolve())
			candidates = list(dict.fromkeys(candidates))

			if not candidates:
				file_stem = external_path.stem.lower()
				for directory in search_directories:
					for path in directory.iterdir():
						if (
							path.is_file()
							and path.suffix.lower() in suffixes
							and path.stem.lower().endswith(f"_{file_stem}")
						):
							candidates.append(path.resolve())
				candidates = list(dict.fromkeys(candidates))

			if len(candidates) > 1:
				raise ValueError(f".EXTERNAL ambiguo: hay varios archivos para {filename}")
			if not candidates:
				expected = " o ".join(f"{filename}{item}" for item in suffixes)
				raise ValueError(f"no se encontró {expected} para .EXTERNAL")
			if candidates[0].parent not in allowed_roots:
				raise ValueError(".EXTERNAL solo puede indicar un archivo del proyecto")
			return candidates[0]

		def parse_external(code):
			match = external_pattern.fullmatch(code)
			if match is None:
				raise ValueError(
					"sintaxis: .EXTERNAL requiere un archivo o ARCHIVO-ETIQUETA"
				)
			specification = next(value for value in match.groups() if value is not None)
			filename, separator, symbol = specification.partition("-")
			if separator and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", symbol):
				raise ValueError(".EXTERNAL requiere una etiqueta válida después del guion")
			return specification, filename, symbol if separator else None

		modules[root_path] = {
			"path": root_path,
			"source": source,
			"imports": [],
		}
		module_order.append(root_path)

		index = 0
		while index < len(module_order):
			module_path = module_order[index]
			module = modules[module_path]
			for line_number, _original, code, first_token in source_lines(module["source"]):
				if first_token != ".EXTERNAL":
					continue
				try:
					specification, filename, symbol = parse_external(code)
					target_path = resolve_external(filename, module_path)
				except ValueError as error:
					errors.append((line_number, f"{module_path.name}: {error}"))
					continue

				module["imports"].append(
					(specification, filename, symbol, target_path, line_number)
				)
				if target_path not in modules:
					try:
						target_source = target_path.read_text(encoding="utf-8-sig")
					except (OSError, UnicodeError) as error:
						errors.append((
							line_number,
							f"{module_path.name}: no se pudo abrir {target_path.name}: {error}",
						))
						continue
					modules[target_path] = {
						"path": target_path,
						"source": target_source,
						"imports": [],
					}
					module_order.append(target_path)
			index += 1

		if errors:
			raise AssemblyError(errors)

		def module_body(module_source):
			body = []
			for _line_number, original, _code, first_token in source_lines(module_source):
				if first_token in (".EXTERNAL", ".ORIG", ".END"):
					continue
				body.append(original)
			return body

		def record_size(record, assembler):
			if record.operation == ".BYTE":
				return len(record.operands)
			if record.operation == ".BLKW":
				return 2 * assembler._parse_number(record.operands[0])
			if record.operation in ("LDRX", "STRX"):
				return 4
			if record.operation in ("LDR", "STR") and len(record.operands) == 3:
				try:
					offset = assembler._parse_number(record.operands[2])
				except ValueError:
					offset = 0
				if not -16 <= offset <= 15:
					return 4
			if (
				record.operation == "ADD"
				and len(record.operands) == 3
				and not re.fullmatch(r"[Rr]\d+", record.operands[2])
				and assembler.fractional_bits
			):
				try:
					immediate = assembler._parse_fixed_value(record.operands[2])
				except ValueError:
					pass
				else:
					if not -16 <= immediate <= 15 and -0x8000 <= immediate <= 0x7FFF:
						return 4
			if record.operation == ".STRINGZ" and len(record.operands) == 1:
				try:
					decoded = assembler._parse_stringz(record.operands[0])
					return (len(decoded) + 1) * 2
				except ValueError:
					return 0
			return 2

		for module_index, module_path in enumerate(module_order):
			module = modules[module_path]
			body = module_body(module["source"])
			if module_index == 0:
				parse_source = "\n".join(
					original
					for _line_number, original, _code, first_token in source_lines(module["source"])
					if first_token != ".EXTERNAL"
				)
			else:
				parse_source = ".ORIG x3000\n" + "\n".join(body) + "\n.END"

			module_assembler = LC3Assembler()
			module_assembler.fractional_bits = self.fractional_bits
			records, origin, module_errors = module_assembler._first_pass(parse_source)
			if module_errors:
				errors.extend(
					(line_number, f"{module_path.name}: {message}")
					for line_number, message in module_errors
				)
				continue
			if origin is None:
				errors.append((1, f"{module_path.name}: falta la directiva .ORIG"))
				continue

			module["body"] = body
			module["labels"] = dict(module_assembler.labels)
			module["origin"] = origin
			module["size"] = max(
				(record.address + record_size(record, module_assembler) - origin)
				for record in records
			) if records else 0
			module["renamed_labels"] = {
				label: f"_LINK{module_index}_{label}"
				for label in module["labels"]
			}

		if errors:
			raise AssemblyError(errors)

		for module_path in module_order:
			module = modules[module_path]
			module["external_replacements"] = {}
			bare_external_labels = {}
			for specification, filename, symbol, target_path, line_number in module["imports"]:
				target_module = modules[target_path]
				if symbol is None:
					for exported_symbol, linked_symbol in target_module["renamed_labels"].items():
						bare_external_labels.setdefault(exported_symbol, set()).add(
							linked_symbol
						)
					continue
				normalized_symbol = symbol.upper()
				if normalized_symbol not in target_module["labels"]:
					errors.append((
						line_number,
						f"{module_path.name}: {symbol} no está definido en {target_path.name}",
					))
					continue
				linked_symbol = target_module["renamed_labels"][normalized_symbol]
				qualified_names = {
					specification.upper(),
					f"{Path(filename).stem}-{symbol}".upper(),
				}
				for qualified_name in qualified_names:
					module["external_replacements"][qualified_name] = linked_symbol
				bare_external_labels.setdefault(normalized_symbol, set()).add(linked_symbol)

			for symbol, linked_symbols in bare_external_labels.items():
				if symbol not in module["labels"] and len(linked_symbols) == 1:
					module["external_replacements"][symbol] = next(iter(linked_symbols))

		if errors:
			raise AssemblyError(errors)

		def rewrite_line(original, module):
			code, separator, comment = self._split_comment(original)
			quoted_parts = re.split(r'("(?:\\.|[^"\\])*")', code)
			replacements = module["external_replacements"]
			qualified_patterns = [
				(
					re.compile(
						r"(?<![A-Za-z0-9_])"
						+ re.escape(name)
						+ r"(?![A-Za-z0-9_])",
						re.IGNORECASE,
					),
					replacement,
				)
				for name, replacement in sorted(
					replacements.items(), key=lambda item: len(item[0]), reverse=True
				)
				if "-" in name
			]

			for part_index in range(0, len(quoted_parts), 2):
				part = quoted_parts[part_index]
				for pattern, replacement in qualified_patterns:
					part = pattern.sub(replacement, part)

				def replace_local_label(match):
					label = match.group(0).upper()
					return module["renamed_labels"].get(
						label,
						replacements.get(label, match.group(0)),
					)

				quoted_parts[part_index] = re.sub(
					r"[A-Za-z_][A-Za-z0-9_]*",
					replace_local_label,
					part,
				)

			rewritten = "".join(quoted_parts)
			return rewritten + (separator + comment if separator else "")

		for module_path in module_order:
			module = modules[module_path]
			rewritten_body = [
				rewrite_line(original, module)
				for original in module["body"]
			]
			module["body"] = self._relax_linked_module(
				rewritten_body,
				module_path.name,
			)

			analysis = LC3Assembler()
			analysis.fractional_bits = self.fractional_bits
			records, _origin, module_errors = analysis._first_pass(
				".ORIG x3000\n" + "\n".join(module["body"]) + "\n.END"
			)
			if module_errors:
				raise AssemblyError([
					(line_number, f"{module_path.name}: {message}")
					for line_number, message in module_errors
				])
			module["size"] = max(
				(record.address + record_size(record, analysis) - 0x3000)
				for record in records
			) if records else 0

		linked_lines = [f".ORIG x{modules[root_path]['origin']:04X}"]
		next_address = modules[root_path]["origin"] + modules[root_path]["size"]
		for module_index, module_path in enumerate(module_order):
			module = modules[module_path]
			if module_index:
				if next_address & 1:
					linked_lines.append(".BYTE #0")
					next_address += 1
				if next_address + module["size"] > 0x10000:
					raise AssemblyError([(
						1,
						f"el enlazado de {module_path.name} excede el espacio de direcciones de 16 bits",
					)])
			linked_lines.extend(module["body"])
			next_address += module["size"] if module_index else 0
		linked_lines.append(".END")
		return "\n".join(linked_lines)

	def _relax_linked_module(self, lines, module_name):
		relaxed_lines = list(lines)
		relaxation_index = 0
		module_tag = re.sub(r"[^A-Za-z0-9_]", "_", Path(module_name).stem.upper())

		def label_line_indices(module_lines, assembler):
			indices = {}
			for line_index, original in enumerate(module_lines):
				code = self._strip_comment(original).strip()
				if not code:
					continue
				tokens = self._split_tokens(code)
				first = tokens[0]
				if first.endswith(":"):
					label = first[:-1]
				elif (
					not assembler._is_operation(first.upper())
					and (len(tokens) == 1 or assembler._is_operation(tokens[1].upper()))
				):
					label = first
				else:
					continue
				indices[label.upper()] = line_index
			return indices

		def replace_branch_target(original, target):
			code, separator, comment = self._split_comment(original)
			tokens = self._split_tokens(code.strip())
			operation_index = 0
			if (
				not self._is_operation(tokens[0].upper())
				and len(tokens) > 1
				and self._is_operation(tokens[1].upper())
			):
				operation_index = 1
			tokens[operation_index + 1] = target
			rewritten = " ".join(tokens)
			return rewritten + (separator + comment if separator else "")

		def lea_expansion(original, destination, target, serial):
			code, separator, comment = self._split_comment(original)
			tokens = self._split_tokens(code.strip())
			operation_index = 0
			if (
				not self._is_operation(tokens[0].upper())
				and len(tokens) > 1
				and self._is_operation(tokens[1].upper())
			):
				operation_index = 1
			label_tokens = tokens[:operation_index]
			pool_label = f"_LINK_{module_tag}_POOL_{serial}"
			skip_label = f"_LINK_{module_tag}_POOL_SKIP_{serial}"
			prefix = " ".join(label_tokens)
			first_instruction = " ".join(
				([prefix] if prefix else []) + ["LEA", destination, pool_label]
			)
			first_instruction += separator + comment if separator else ""
			return [
				first_instruction,
				f"LDR {destination} {destination} #0",
				f"BRnzp {skip_label}",
				f"{pool_label} .FILL {target}",
				skip_label,
			]

		for _ in range(2048):
			analysis = LC3Assembler()
			analysis.fractional_bits = self.fractional_bits
			module_source = ".ORIG x3000\n" + "\n".join(relaxed_lines) + "\n.END"
			records, _origin, errors = analysis._first_pass(module_source)
			if errors:
				raise AssemblyError([
					(line_number, f"{module_name}: {message}")
					for line_number, message in errors
				])

			labels = analysis.labels
			label_lines = label_line_indices(relaxed_lines, analysis)
			changed = False

			for record in records:
				if record.operation in ("LD", "ST") and len(record.operands) == 2:
					destination = record.operands[0].upper()
					operand = record.operands[1].upper()
					if operand not in labels:
						continue
					difference = labels[operand] - (record.address + 2)
					if difference % 2 == 0 and not -128 <= difference // 2 <= 127:
						line_index = record.number - 2
						relaxation_index += 1
						pool_label = f"_LINK_{module_tag}_DATA_POOL_{relaxation_index}"
						skip_label = f"_LINK_{module_tag}_DATA_SKIP_{relaxation_index}"

						code, separator, comment = self._split_comment(relaxed_lines[line_index])
						tokens = self._split_tokens(code.strip())
						operation_index = 0
						if (
							not self._is_operation(tokens[0].upper())
							and len(tokens) > 1
							and self._is_operation(tokens[1].upper())
						):
							operation_index = 1
						label_prefix = " ".join(tokens[:operation_index])

						if record.operation == "LD":
							prefix = f"{label_prefix} " if label_prefix else ""
							expansion = [
								f"{prefix}LEA {destination} {pool_label}",
								f"LDR {destination} {destination} #0",
								f"LDR {destination} {destination} #0",
								f"BRnzp {skip_label}",
								f"{pool_label} .FILL {record.operands[1]}",
								skip_label,
							]
						else:
							scratch = next(
								register
								for register in ("R6", "R5", "R4", "R3", "R2", "R1", "R0")
								if register != destination
							)
							save_label = f"_LINK_{module_tag}_DATA_SAVE_{relaxation_index}"
							prefix = f"{label_prefix} " if label_prefix else ""
							expansion = [
								f"{prefix}ST {scratch} {save_label}",
								f"LEA {scratch} {pool_label}",
								f"LDR {scratch} {scratch} #0",
								f"STR {destination} {scratch} #0",
								f"LD {scratch} {save_label}",
								f"BRnzp {skip_label}",
								f"{save_label} .BLKW 1",
								f"{pool_label} .FILL {record.operands[1]}",
								skip_label,
							]

						relaxed_lines[line_index:line_index + 1] = expansion
						changed = True
						break

				if record.operation == "LEA":
					operand = record.operands[1].upper()
					if operand not in labels:
						continue
					difference = labels[operand] - (record.address + 2)
					if difference % 2 == 0 and not -128 <= difference // 2 <= 127:
						line_index = record.number - 2
						relaxation_index += 1
						relaxed_lines[line_index:line_index + 1] = lea_expansion(
							relaxed_lines[line_index],
							record.operands[0],
							record.operands[1],
							relaxation_index,
						)
						changed = True
						break

				if (
					record.operation not in BRANCH_CONDITIONS
					and record.operation not in BRANCH_FLAGS
					and record.operation != "JSR"
				):
					continue
				operand = record.operands[0].upper()
				if operand not in labels:
					continue
				bit_count = 10 if record.operation == "JSR" else 8
				difference = labels[operand] - (record.address + 2)
				if difference % 2:
					continue
				offset = difference // 2
				minimum = -(1 << (bit_count - 1))
				maximum = (1 << (bit_count - 1)) - 1
				if minimum <= offset <= maximum:
					continue

				target_line = label_lines.get(operand)
				source_line = record.number - 2
				if target_line is None or target_line == source_line:
					continue

				forward = labels[operand] > record.address
				relay_points = []
				current_address = record.address + 2
				step_words = 80 if record.operation != "JSR" else 300
				while abs(labels[operand] - current_address) > (
					100 if record.operation != "JSR" else 400
				) * 2:
					desired_address = current_address + (step_words * 2 if forward else -step_words * 2)
					candidates = [
						(item.address, item.number - 2)
						for item in records
						if (
							(source_line < item.number - 2 < target_line)
							if forward
							else (target_line < item.number - 2 < source_line)
						)
						and (
							item.address >= desired_address
							if forward
							else item.address <= desired_address
						)
					]
					if not candidates:
						break
					candidate = (
						min(candidates, key=lambda item: item[0])
						if forward
						else max(candidates, key=lambda item: item[0])
					)
					if candidate[1] in relay_points:
						break
					relay_points.append(candidate[1])
					current_address = candidate[0] + 4

				relay_points.append(target_line)
				relaxation_index += 1
				relay_labels = [
					f"_LINK_{module_tag}_RELAY_{relaxation_index}_{index}"
					for index in range(len(relay_points))
				]
				relaxed_lines[source_line] = replace_branch_target(
					relaxed_lines[source_line],
					relay_labels[0],
				)

				insertions = {}
				for index, line_index in enumerate(relay_points):
					next_target = (
						relay_labels[index + 1]
						if index + 1 < len(relay_labels)
						else operand
					)
					skip_label = (
						f"_LINK_{module_tag}_RELAY_SKIP_{relaxation_index}_{index}"
					)
					insertions.setdefault(line_index, []).extend([
						f"BRnzp {skip_label}",
						f"{relay_labels[index]} BRnzp {next_target}",
						skip_label,
					])

				with_islands = []
				for line_index, original in enumerate(relaxed_lines):
					with_islands.extend(insertions.get(line_index, ()))
					with_islands.append(original)
				if len(relaxed_lines) in insertions:
					with_islands.extend(insertions[len(relaxed_lines)])
				relaxed_lines = with_islands
				changed = True
				break

			if not changed:
				return relaxed_lines

		raise AssemblyError([(1, f"{module_name}: no se pudieron relajar los saltos largos")])

	@staticmethod
	def _listing_instruction(record):
		if record.operands:
			return f"{record.operation} {', '.join(record.operands)}"
		return record.operation

	def detect_format(self, source):
		active_lines = [
			(line_number, self._strip_comment(original).strip())
			for line_number, original in enumerate(source.splitlines(), start=1)
			if self._strip_comment(original).strip()
		]
		if not active_lines:
			return "ASM"

		for _line_number, text in active_lines:
			tokens = [token.rstrip(":").upper() for token in re.split(r"[\s,]+", text)]
			if any(self._is_operation(token) for token in tokens[:2]):
				return "ASM"

		line_number, first = active_lines[0]
		if first.startswith("@"):
			address = first[1:].strip()
			if re.fullmatch(r"[01]{16}", address):
				return "BINARIO"
			if re.fullmatch(r"(?:0[xX]|[xX])?[0-9A-Fa-f]{1,4}", address):
				return "HEXADECIMAL"
			raise AssemblyError([(line_number, "dirección inicial inválida para código máquina")])

		if re.fullmatch(r"[01]{16}", first):
			return "BINARIO"
		if re.fullmatch(r"(?:0[xX]|[xX])?[0-9A-Fa-f]{4}", first):
			return "HEXADECIMAL"
		if first.startswith(".") or re.match(r"[A-Za-z_]", first):
			return "ASM"
		raise AssemblyError([(line_number, "formato no reconocido; use ASM, palabras binarias de 16 bits o palabras hexadecimales de 4 dígitos")])

	def _assemble_machine_code(self, source, source_format):
		origin = None
		words = []
		errors = []

		for line_number, original in enumerate(source.splitlines(), start=1):
			comment = original.split(";", 1)[1] if ";" in original else ""
			match = re.search(r"\b(?:origen|origin)\s*:\s*(?:0[xX]|[xX])?([0-9a-f]{1,4})\b", comment, re.IGNORECASE)
			if match:
				comment_origin = int(match.group(1), 16)
				if origin is not None and origin != comment_origin:
					errors.append((line_number, "se indicaron direcciones de origen diferentes"))
				else:
					origin = comment_origin

		for line_number, original in enumerate(source.splitlines(), start=1):
			text = original.split(";", 1)[0].strip()
			if not text:
				continue

			if text.startswith("@"):
				address = text[1:].strip()
				if source_format == "BINARIO" and re.fullmatch(r"[01]{16}", address):
					header_origin = int(address, 2)
				elif source_format == "HEXADECIMAL":
					match = re.fullmatch(r"(?:0[xX]|[xX])?([0-9A-Fa-f]{1,4})", address)
					if match:
						header_origin = int(match.group(1), 16)
					else:
						errors.append((line_number, "dirección hexadecimal inválida; use el formato @x3000, @0x3000 o @3000"))
						continue
				else:
					errors.append((line_number, "dirección binaria inválida; se requieren 16 bits"))
					continue
				if origin is not None and origin != header_origin:
					errors.append((line_number, "la dirección inicial no coincide con el comentario de origen"))
				else:
					origin = header_origin
				continue

			if source_format == "BINARIO":
				if not re.fullmatch(r"[01]{16}", text):
					errors.append((line_number, "palabra binaria inválida; se requieren exactamente 16 bits"))
					continue
				words.append(int(text, 2))
			else:
				match = re.fullmatch(r"(?:0[xX]|[xX])?([0-9A-Fa-f]{4})", text)
				if not match:
					errors.append((line_number, "palabra hexadecimal inválida; use el formato x0000, 0x0000 o 0000"))
					continue
				words.append(int(match.group(1), 16))

		if origin is None:
			errors.append((1, "falta la dirección de origen; use @x3000 o un comentario '; Origen: x3000'"))
		elif not 0 <= origin <= 0xFFFF or origin & 1:
			errors.append((1, "la dirección de origen debe ser par y estar entre 0 y 65535"))
		if not words:
			errors.append((1, "no hay palabras de código máquina"))
		if origin is not None and origin + len(words) * 2 > 0x10000:
			errors.append((1, "el programa excede el espacio de direcciones de 16 bits"))
		if errors:
			raise AssemblyError(errors)
		return origin, words

	def _first_pass(self, source):
		records = []
		self.labels = {}
		errors = []
		current_address = None
		origin = None
		ended = False
		pending_labels = []

		for line_number, original in enumerate(source.splitlines(), start=1):
			text = self._strip_comment(original).strip()
			if not text:
				continue
			if ended:
				errors.append((line_number, "hay código después de .END"))
				continue

			tokens = self._split_tokens(text)
			label = None
			first = tokens[0]
			if first.endswith(":"):
				label = first[:-1]
				tokens = tokens[1:]
			elif (
				not self._is_operation(first.upper())
				and (len(tokens) == 1 or self._is_operation(tokens[1].upper()))
			):
				label = first
				tokens = tokens[1:]

			if label and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
				errors.append((line_number, f"etiqueta inválida: {label}"))
				label = None

			if not tokens:
				if label is not None:
					if current_address is None:
						errors.append((line_number, "la etiqueta aparece antes de .ORIG"))
					else:
						pending_labels.append((label, line_number))
				continue

			operation = tokens[0].upper()
			operands = tokens[1:]
			if operation == ".ORIG":
				if origin is not None or current_address is not None:
					errors.append((line_number, ".ORIG debe aparecer una sola vez al inicio"))
					continue
				if label is not None:
					errors.append((line_number, "no se permite una etiqueta en .ORIG"))
				try:
					self._expect_count(operands, 1)
					origin = self._parse_number(operands[0])
					if not 0 <= origin <= 0xFFFF:
						raise ValueError("la dirección de .ORIG debe estar entre 0 y 65535")
					if origin & 1:
						raise ValueError(".ORIG debe ser una dirección par")
					current_address = origin
				except ValueError as error:
					errors.append((line_number, str(error)))
					current_address = None
				continue

			if operation == ".END":
				if operands:
					errors.append((line_number, ".END no recibe operandos"))
				for pending_label, pending_line in pending_labels:
					self._add_label(
						pending_label, current_address, pending_line, errors
					)
				pending_labels.clear()
				ended = True
				continue

			if current_address is None:
				errors.append((line_number, "se requiere .ORIG antes del código"))
				continue

			record_valid = True
			size = 2
			if operation == ".BYTE":
				size = len(operands)
			elif operation in ("LDRX", "STRX"):
				size = 4
			elif operation in ("LDR", "STR") and len(operands) == 3:
				try:
					offset = self._parse_number(operands[2])
					if not -16 <= offset <= 15:
						size = 4
				except ValueError:
					pass
			elif (
				operation == "ADD"
				and len(operands) == 3
				and not re.fullmatch(r"[Rr]\d+", operands[2])
				and self.fractional_bits
			):
				try:
					immediate = self._parse_fixed_value(operands[2])
				except ValueError:
					pass
				else:
					if not -16 <= immediate <= 15 and -0x8000 <= immediate <= 0x7FFF:
						size = 4
			elif operation == ".STRINGZ":
				try:
					self._expect_count(operands, 1)
					decoded_string = self._parse_stringz(operands[0])
					size = (len(decoded_string) + 1) * 2
				except ValueError as error:
					errors.append((line_number, str(error)))
					size = 0
					record_valid = False
			elif operation == ".BLKW":
				try:
					self._expect_count(operands, 1)
					count = self._parse_number(operands[0])
					if count < 0:
						raise ValueError(".BLKW requiere un tamaño no negativo")
					size = count * 2
				except ValueError as error:
					errors.append((line_number, str(error)))
					size = 0
					record_valid = False
			if operation != ".BYTE" and current_address & 1:
				current_address += 1
			for pending_label, pending_line in pending_labels:
				self._add_label(
					pending_label, current_address, pending_line, errors
				)
			pending_labels.clear()
			if label is not None:
				self._add_label(label, current_address, line_number, errors)

			if record_valid:
				records.append(SourceLine(line_number, current_address, operation, operands))
			current_address += size
			if current_address > 0x10000:
				errors.append((line_number, "el programa excede el espacio de direcciones de 16 bits"))

		for pending_label, pending_line in pending_labels:
			if current_address is not None:
				self._add_label(pending_label, current_address, pending_line, errors)

		if origin is None:
			errors.append((1, "falta la directiva .ORIG"))
		return records, origin, errors

	def _add_label(self, label, address, line_number, errors):
		normalized = label.upper()
		if normalized in self.labels:
			errors.append((line_number, f"etiqueta duplicada: {label}"))
		else:
			self.labels[normalized] = address

	def _is_operation(self, token):
		return (
			token in OPCODES
			or token in BRANCH_CONDITIONS
			or token in BRANCH_FLAGS
			or token in DIRECTIVES
			or token in PSEUDO_OPS
		)

	@staticmethod
	def _split_tokens(text):
		tokens = []
		current = []
		in_quotes = False
		escaped = False
		for character in text:
			if escaped:
				current.append(character)
				escaped = False
				continue
			if character == "\\" and in_quotes:
				current.append(character)
				escaped = True
				continue
			if character == '"':
				in_quotes = not in_quotes
				current.append(character)
				continue
			if not in_quotes and (character.isspace() or character == ","):
				if current:
					tokens.append("".join(current))
					current = []
				continue
			current.append(character)
		if current:
			tokens.append("".join(current))
		return tokens

	def _encode(self, line):
		operation = line.operation
		operands = line.operands

		if operation == ".STRINGZ":
			self._expect_count(operands, 1)
			decoded = self._parse_stringz(operands[0])
			return [ord(character) for character in decoded] + [0]

		if operation == ".BYTE":
			if not operands:
				raise ValueError(".BYTE requiere al menos un valor")
			values = []
			for operand in operands:
				value = self._parse_value(operand)
				if not -0x80 <= value <= 0xFF:
					raise ValueError(
						f".BYTE fuera de rango: {value} (permitido -128..255)"
					)
				values.append(value & 0xFF)
			return values

		if operation == ".FILL":
			self._expect_count(operands, 1)
			value = self._parse_fixed_value(operands[0])
			if self._is_decimal_literal(operands[0]) and not -0x8000 <= value <= 0x7FFF:
				raise ValueError(
					f".FILL fuera de rango para el formato Q: {value} "
					"(permitido -32768..32767)"
				)
			if not -0x8000 <= value <= 0xFFFF:
				raise ValueError(".FILL debe estar entre -32768 y 65535")
			return value & 0xFFFF

		if operation == ".BLKW":
			count = self._parse_number(operands[0])
			return [0] * count

		if operation in BRANCH_CONDITIONS:
			self._expect_count(operands, 1)
			offset = self._pc_offset(operands[0], line, 8)
			return (BRANCH_CONDITIONS[operation] << 8) | (offset & 0xFF)

		if operation in BRANCH_FLAGS:
			self._expect_count(operands, 1)
			offset = self._pc_offset(operands[0], line, 8)
			return (BRANCH_FLAGS[operation] << 11) | (offset & 0xFF)

		if operation in ("ADD", "AND", "SUB", "ADDI5"):
			self._expect_count(operands, 3)
			destination = self._register(operands[0])
			source = self._register(operands[1])
			prefix = (OPCODES[operation] << 11) | (destination << 8) | (source << 5)
			if operation == "ADDI5":
				if re.fullmatch(r"[Rr]\d+", operands[2]):
					raise ValueError("ADDI5 requiere un operando inmediato")
				immediate = self._parse_fixed_value(operands[2])
				self._check_signed(immediate, 5, "inmediato")
				return prefix | (immediate & 0x1F)
			if re.fullmatch(r"[Rr]\d+", operands[2]):
				return prefix | self._register(operands[2])
			immediate = (
				self._parse_fixed_value(operands[2])
				if operation in ("ADD", "SUB")
				else self._parse_number(operands[2])
			)
			if -8 <= immediate <= 7:
				return prefix | 0b10000 | (immediate & 0xF)
			if operation == "ADD" and -16 <= immediate <= 15:
				return (
					(OPCODES["ADDI5"] << 11)
					| (destination << 8)
					| (source << 5)
					| (immediate & 0x1F)
				)
			if operation == "ADD" and self.fractional_bits:
				self._check_signed(immediate, 16, "valor en formato Q")
				extended_prefix = (0b10010 << 11) | (destination << 8) | (source << 5)
				return [extended_prefix, immediate & 0xFFFF]
			self._check_signed(immediate, 5 if operation == "ADD" else 4, "inmediato")
			return prefix | 0b10000 | (immediate & 0xF)

		if operation in ("MUL", "MULH"):
			self._expect_count(operands, 3)
			if not re.fullmatch(r"[Rr]\d+", operands[2]):
				raise ValueError(f"{operation} solo admite registros (no inmediatos)")
			destination = self._register(operands[0])
			source = self._register(operands[1])
			return (
				(OPCODES[operation] << 11)
				| (destination << 8)
				| (source << 5)
				| self._register(operands[2])
			)

		if operation in ("LSHF", "RSHFL", "RSHFA"):
			self._expect_count(operands, 3)
			destination = self._register(operands[0])
			source = self._register(operands[1])
			amount = self._parse_number(operands[2])
			if not 0 <= amount <= 15:
				raise ValueError(f"cantidad de desplazamiento fuera de rango: {amount} (permitido 0..15)")
			return (
				(OPCODES[operation] << 11)
				| (destination << 8)
				| (source << 5)
				| amount
			)

		if operation == "JSR":
			self._expect_count(operands, 1)
			offset = self._pc_offset(operands[0], line, 10)
			return (OPCODES[operation] << 11) | 0x400 | (offset & 0x3FF)

		if operation in ("LD", "ST"):
			self._expect_count(operands, 2)
			register = self._register(operands[0])
			offset = self._pc_offset(operands[1], line, 8)
			return (
				(OPCODES[operation] << 11)
				| (register << 8)
				| (offset & 0xFF)
			)

		if operation == "JSRR":
			self._expect_count(operands, 1)
			base = self._register(operands[0])
			return (OPCODES["JSR"] << 11) | (base << 5)

		if operation in ("LDRX", "STRX"):
			self._expect_count(operands, 3)
			register = self._register(operands[0])
			base = self._register(operands[1])
			offset = self._parse_number(operands[2])
			self._check_signed(offset, 16, "offset")
			return [
				(OPCODES[operation] << 11)
				| (register << 8)
				| (base << 5),
				offset & 0xFFFF,
			]

		if operation in ("LDR", "STR", "LDB", "STB", "LDH", "STH"):
			self._expect_count(operands, 3)
			register = self._register(operands[0])
			base = self._register(operands[1])
			offset = self._parse_number(operands[2])
			if operation in ("LDR", "STR") and not -16 <= offset <= 15:
				self._check_signed(offset, 16, "offset")
				extended_operation = "LDRX" if operation == "LDR" else "STRX"
				return [
					(OPCODES[extended_operation] << 11)
					| (register << 8)
					| (base << 5),
					offset & 0xFFFF,
				]
			self._check_signed(offset, 5, "offset")
			return (
				(OPCODES[operation] << 11)
				| (register << 8)
				| (base << 5)
				| (offset & 0x1F)
			)

		if operation == "RTI":
			self._expect_count(operands, 0)
			return OPCODES[operation] << 11

		if operation == "NOT":
			self._expect_count(operands, 2)
			destination = self._register(operands[0])
			source = self._register(operands[1])
			return (OPCODES[operation] << 11) | (destination << 8) | (source << 5) | 0x1F

		if operation in ("JMP", "RET"):
			self._expect_count(operands, 0 if operation == "RET" else 1)
			base = 7 if operation == "RET" else self._register(operands[0])
			return (OPCODES["JMP"] << 11) | (base << 5)

		if operation == "LEA":
			self._expect_count(operands, 2)
			destination = self._register(operands[0])
			offset = self._pc_offset(operands[1], line, 8)
			return (OPCODES[operation] << 11) | (destination << 8) | (offset & 0xFF)

		if operation in ("TRAP", "HALT", "GETC", "OUT", "PUTS", "IN", "PUTSP"):
			if operation == "TRAP":
				self._expect_count(operands, 1)
				vector_name = operands[0].upper()
				if vector_name in TRAP_VECTORS:
					vector = TRAP_VECTORS[vector_name]
				else:
					vector = self._parse_value(operands[0])
			else:
				self._expect_count(operands, 0)
				vector = TRAP_VECTORS[operation]
			if not 0 <= vector <= 0xFF:
				raise ValueError("el vector TRAP debe estar entre 0 y 255")
			return (OPCODES["TRAP"] << 11) | vector

		raise ValueError(f"operación desconocida o no soportada: {operation}")

	def _pc_offset(self, operand, line, bit_count):
		normalized = operand.upper()
		if normalized in self.labels:
			difference = self.labels[normalized] - (line.address + 2)
			if difference % 2:
				raise ValueError(f"la etiqueta {operand} no está alineada a palabra")
			offset = difference // 2
		else:
			try:
				offset = self._parse_number(operand)
			except ValueError as error:
				if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", operand):
					raise ValueError(f"etiqueta no definida: {operand}") from error
				raise ValueError(f"PCoffset inválido: {operand}") from error
		self._check_signed(offset, bit_count, "PCoffset")
		return offset

	@staticmethod
	def _expect_count(operands, expected):
		if len(operands) != expected:
			raise ValueError(f"se esperaban {expected} operandos y se recibieron {len(operands)}")

	@staticmethod
	def _register(token):
		match = re.fullmatch(r"[Rr]([0-7])", token)
		if not match:
			raise ValueError(f"registro inválido: {token}; usa R0 a R7")
		return int(match.group(1))

	@staticmethod
	def _check_signed(value, bit_count, name):
		minimum = -(1 << (bit_count - 1))
		maximum = (1 << (bit_count - 1)) - 1
		if not minimum <= value <= maximum:
			raise ValueError(f"{name} fuera de rango: {value} (permitido {minimum}..{maximum})")

	@staticmethod
	def _parse_number(token):
		sign = 1
		value = token.strip()
		if value.startswith(("+", "-")):
			if value[0] == "-":
				sign = -1
			value = value[1:]
		if value.startswith("#"):
			number = int(value[1:], 10)
		elif value[:1].lower() == "x":
			number = int(value[1:], 16)
		elif value[:1].lower() == "b":
			number = int(value[1:], 2)
		elif value.lower().startswith("0x"):
			number = int(value[2:], 16)
		elif value.lower().startswith("0b"):
			number = int(value[2:], 2)
		else:
			number = int(value, 10)
		return sign * number

	def _parse_value(self, token):
		normalized = token.upper()
		if normalized in self.labels:
			return self.labels[normalized] // 2
		expression = re.fullmatch(
			r"([A-Za-z_][A-Za-z0-9_]*)\s*([+-])\s*([A-Za-z_][A-Za-z0-9_]*)",
			token,
		)
		if expression:
			left_name, operator, right_name = expression.groups()
			left_name = left_name.upper()
			right_name = right_name.upper()
			if left_name not in self.labels:
				raise ValueError(f"etiqueta no definida: {left_name}")
			if right_name not in self.labels:
				raise ValueError(f"etiqueta no definida: {right_name}")
			value = self.labels[left_name] // 2
			if operator == "+":
				value += self.labels[right_name] // 2
			else:
				value -= self.labels[right_name] // 2
			return value
		try:
			return self._parse_number(token)
		except ValueError as error:
			if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
				raise ValueError(f"etiqueta no definida: {token}") from error
			raise ValueError(f"valor inválido: {token}") from error

	def _parse_fixed_value(self, token):
		value = token.strip()
		if value.startswith("#"):
			value = value[1:]
		if not self._is_decimal_literal(value):
			return self._parse_value(token)
		try:
			scaled = Decimal(value) * (1 << self.fractional_bits)
			if not scaled.is_finite():
				raise InvalidOperation
		except InvalidOperation as error:
			raise ValueError(f"valor decimal inválido: {token}") from error
		return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))

	@staticmethod
	def _decode_string(text):
		characters = []
		index = 0
		escapes = {
			"n": ord("\n"),
			"r": ord("\r"),
			"t": ord("\t"),
			"0": 0,
			'"': ord('"'),
			"\\": ord("\\"),
		}
		while index < len(text):
			if text[index] == "\\" and index + 1 < len(text):
				characters.append(escapes.get(text[index + 1], ord(text[index + 1])))
				index += 2
			else:
				characters.append(ord(text[index]))
				index += 1
		return characters

	@staticmethod
	def _is_decimal_literal(token):
		value = token.strip()
		if value.startswith("#"):
			value = value[1:]
		return re.fullmatch(
			r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
			value,
		) is not None


def assemble_file(input_path, output_path=None, fractional_bits=0, output_format="hex"):
	if output_format not in ("hex", "bin"):
		raise ValueError("el formato de salida debe ser 'hex' o 'bin'")
	source_path = Path(input_path)
	source = source_path.read_text(encoding="utf-8-sig")
	origin, words = LC3Assembler().assemble(
		source,
		fractional_bits=fractional_bits,
		source_path=source_path,
	)
	default_suffix = ".bin" if output_format == "bin" else ".hex"
	destination = Path(output_path) if output_path else source_path.with_suffix(default_suffix)
	if output_format == "bin":
		contents = f"@{origin:016b}\n" + "".join(f"{word:016b}\n" for word in words)
	else:
		contents = f"@x{origin:04X}\n" + "".join(f"x{word:04X}\n" for word in words)
	destination.write_text(contents, encoding="ascii")
	return destination


def main(argv=None):
	parser = argparse.ArgumentParser(description="Ensamblador para la ISA LC-3 de 16 bits")
	parser.add_argument("archivo", help="archivo de texto .asm o .txt")
	parser.add_argument("-o", "--output", help="archivo de salida (.hex o .bin)")
	parser.add_argument(
		"-q",
		"--fractional-bits",
		type=int,
		default=0,
		help="cantidad de bits fraccionarios para formato Q (0 a 15, por defecto 0)",
	)
	parser.add_argument(
		"-f",
		"--format",
		choices=("hex", "bin"),
		default="hex",
		help="formato de salida: hex o bin (por defecto hex)",
	)
	args = parser.parse_args(argv)

	try:
		output_path = assemble_file(
			args.archivo,
			args.output,
			fractional_bits=args.fractional_bits,
			output_format=args.format,
		)
	except (OSError, ValueError, AssemblyError) as error:
		if isinstance(error, AssemblyError):
			for line, message in error.diagnostics:
				print(f"{args.archivo}:{line}: error: {message}", file=sys.stderr)
		else:
			print(f"{args.archivo}: error: {error}", file=sys.stderr)
		return 1

	print(f"Ensamblado correcto: {output_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
