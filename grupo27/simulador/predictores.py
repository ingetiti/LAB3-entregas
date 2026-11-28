'''
Predictores de salto para el simulador de la arquitectura ISA-G27.

Este módulo implementa las estrategias de predicción de saltos para las etapas
del pipeline y control de flujo del simulador:
- Predictor de salto nunca tomado (Never Taken)
- Predictor de salto siempre tomado (Always Taken)
- Predictor dinámico de 1 bit (No tomado, Tomado)
- Predictor dinámico de 2 bits con contador saturado (Fuertemente no tomado,
  Débilmente no tomado, Débilmente tomado, Fuertemente tomado)

El diseño es modular y desacoplado del simulador y ensamblador; para agregar nuevos
predictores (como predictores con historial global/local, BTB o predictores de 2 niveles)
solo es necesario heredar de BASE_PREDICTOR e implementarlos en este archivo.
'''


class BASE_PREDICTOR:
    """
    Clase base para todos los predictores de salto del simulador.
    Maneja las métricas de aciertos, fallos y la interfaz común.
    """
    NAME = "Base Predictor"

    def __init__(self):
        self.total_predictions = 0
        self.correct_predictions = 0
        self.mispredictions = 0

    def predict(self, pc=None, target_pc=None) -> bool:
        """
        Devuelve la predicción del salto:
        - True: Predice que el salto SERÁ tomado (branch taken).
        - False: Predice que el salto NO será tomado (branch not taken).

        Parámetros:
        - pc (int, opcional): Dirección en memoria de la instrucción de salto.
        - target_pc (int, opcional): Dirección de destino del salto si se conoce.
        """
        raise NotImplementedError("Cada predictor debe implementar predict()")

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        """
        Actualiza el estado interno del predictor tras resolverse el salto
        en la etapa correspondiente (Execute o Writeback) y registra estadísticas.

        Parámetros:
        - pc (int): Dirección de la instrucción de salto.
        - actually_taken (bool): Si la condición del salto se cumplió realmente.
        - target_pc (int, opcional): Dirección de destino real tomada.

        Retorna:
        - bool: True si la predicción fue correcta, False si hubo fallo (misprediction).
        """
        raise NotImplementedError("Cada predictor debe implementar update()")

    def reset(self):
        """Reinicia las estadísticas y el estado del predictor."""
        self.total_predictions = 0
        self.correct_predictions = 0
        self.mispredictions = 0

    @property
    def accuracy(self) -> float:
        """Calcula el porcentaje de precisión de las predicciones (0.0 a 100.0)."""
        if self.total_predictions == 0:
            return 0.0
        return (self.correct_predictions / self.total_predictions) * 100.0

    def get_stats(self) -> dict:
        """Devuelve un diccionario con las métricas acumuladas del predictor."""
        return {
            "name": self.NAME,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "mispredictions": self.mispredictions,
            "accuracy_percent": round(self.accuracy, 2)
        }

    def __str__(self):
        return f"{self.NAME} (Precisión: {self.accuracy:.1f}%, Total: {self.total_predictions})"

    def __repr__(self):
        return f"<{self.__class__.__name__} correct={self.correct_predictions}/{self.total_predictions}>"



# ---------------------------------------------------------------------------
# 1. Predictor Estático: Nunca Tomado (Never Taken)
# ---------------------------------------------------------------------------

class Predictor_Never_taken(BASE_PREDICTOR):
    """
    Predictor estático: siempre predice que el salto condicional NO será tomado.
    Estrategia por defecto típica en procesadores clásicos simples.
    """
    NAME = "Salto Nunca Tomado (Never Taken)"

    def predict(self, pc=None, target_pc=None) -> bool:
        return False

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        predicted = False
        was_correct = (predicted == actually_taken)

        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        else:
            self.mispredictions += 1

        return was_correct



# ---------------------------------------------------------------------------
# 2. Predictor Estático: Siempre Tomado (Always Taken)
# ---------------------------------------------------------------------------

class Predictor_Always_taken(BASE_PREDICTOR):
    """
    Predictor estático: siempre predice que el salto condicional SÍ será tomado.
    """
    NAME = "Salto Siempre Tomado (Always Taken)"

    def predict(self, pc=None, target_pc=None) -> bool:
        return True

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        predicted = True
        was_correct = (predicted == actually_taken)

        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        else:
            self.mispredictions += 1

        return was_correct



# ---------------------------------------------------------------------------
# 3. Predictor Dinámico: 1 Bit por entrada de salto
# ---------------------------------------------------------------------------

class Predictor_1_bit(BASE_PREDICTOR):
    """
    Predictor dinámico de 1 bit:
    Guarda el último comportamiento de cada instrucción de salto (indexada por su PC).
    Estados:
    - 0: No Tomado (Predict False)
    - 1: Tomado    (Predict True)
    """
    NAME = "Predictor de 1 Bit"

    def __init__(self, default_state: int = 0):
        super().__init__()
        self.default_state = 1 if default_state else 0
        self.table = {}  # Mapea pc -> estado (0 o 1)

    def predict(self, pc=None, target_pc=None) -> bool:
        state = self.table.get(pc, self.default_state) if pc is not None else self.default_state
        return bool(state == 1)

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        state = self.table.get(pc, self.default_state) if pc is not None else self.default_state
        predicted = bool(state == 1)
        was_correct = (predicted == actually_taken)

        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        else:
            self.mispredictions += 1

        # Actualiza el estado al último resultado observado
        if pc is not None:
            self.table[pc] = 1 if actually_taken else 0

        return was_correct

    def reset(self):
        super().reset()
        self.table.clear()



# ---------------------------------------------------------------------------
# 4. Predictor Dinámico: 2 Bits con Contador Saturado (Smith Predictor)
# ---------------------------------------------------------------------------

class Predictor_2_bits(BASE_PREDICTOR):
    """
    Predictor dinámico de 2 bits con contador saturado:
    Requiere dos fallos consecutivos para cambiar de tendencia (tomado / no tomado).
    Estados:
    - 00 (0): Fuertemente No Tomado (Strongly Not Taken) -> Predice False
    - 01 (1): Débilmente No Tomado  (Weakly Not Taken)   -> Predice False
    - 10 (2): Débilmente Tomado     (Weakly Taken)       -> Predice True
    - 11 (3): Fuertemente Tomado    (Strongly Taken)     -> Predice True
    """
    NAME = "Predictor de 2 Bits (Contador Saturado)"

    STRONGLY_NOT_TAKEN = 0
    WEAKLY_NOT_TAKEN   = 1
    WEAKLY_TAKEN       = 2
    STRONGLY_TAKEN     = 3

    def __init__(self, default_state: int = 1):
        """
        Por defecto inicializa en Débilmente No Tomado (1).
        """
        super().__init__()
        self.default_state = max(0, min(3, default_state))
        self.table = {}  # Mapea pc -> estado (0..3)

    def predict(self, pc=None, target_pc=None) -> bool:
        state = self.table.get(pc, self.default_state) if pc is not None else self.default_state
        # Si el bit más significativo es 1 (estados 2 o 3), predice Tomado
        return state >= self.WEAKLY_TAKEN

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        state = self.table.get(pc, self.default_state) if pc is not None else self.default_state
        predicted = (state >= self.WEAKLY_TAKEN)
        was_correct = (predicted == actually_taken)

        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        else:
            self.mispredictions += 1

        # Transición en el contador saturado de 2 bits
        if actually_taken:
            new_state = min(self.STRONGLY_TAKEN, state + 1)
        else:
            new_state = max(self.STRONGLY_NOT_TAKEN, state - 1)

        if pc is not None:
            self.table[pc] = new_state

        return was_correct

    def reset(self):
        super().reset()
        self.table.clear()



# ---------------------------------------------------------------------------
# Base para futuros predictores con Historial (BTB / Branch History Table)
# ---------------------------------------------------------------------------

class Predictor_With_History(BASE_PREDICTOR):
    """
    Estructura base para implementar a futuro predictores con historial de saltos
    (dirección del salto y dirección de destino) con 1 o 2 bits por entrada.
    """
    NAME = "Predictor con Historial (BTB)"

    def __init__(self, history_entries: int = 64, bits_per_entry: int = 2):
        super().__init__()
        self.max_entries = history_entries
        self.bits = bits_per_entry
        # Mapea pc -> {"target": target_address, "state": int}
        self.history = {}

    def predict(self, pc=None, target_pc=None) -> bool:
        if pc is None or pc not in self.history:
            return False
        entry = self.history[pc]
        if self.bits == 1:
            return bool(entry["state"] == 1)
        return entry["state"] >= 2

    def predict_target(self, pc):
        """Devuelve la dirección de destino predicha si está en el historial."""
        if pc in self.history:
            return self.history[pc].get("target")
        return None

    def update(self, pc, actually_taken: bool, target_pc=None) -> bool:
        predicted = self.predict(pc, target_pc)
        was_correct = (predicted == actually_taken)

        self.total_predictions += 1
        if was_correct:
            self.correct_predictions += 1
        else:
            self.mispredictions += 1

        if pc is not None:
            entry = self.history.get(pc, {"target": target_pc, "state": 1 if self.bits == 2 else 0})
            if target_pc is not None and actually_taken:
                entry["target"] = target_pc

            state = entry["state"]
            if self.bits == 1:
                entry["state"] = 1 if actually_taken else 0
            else:
                entry["state"] = min(3, state + 1) if actually_taken else max(0, state - 1)

            self.history[pc] = entry

        return was_correct

    def reset(self):
        super().reset()
        self.history.clear()



# ---------------------------------------------------------------------------
# Aliases y Registro de Predictores
# ---------------------------------------------------------------------------

Predictor_1Bit  = Predict_1_bit = Predictor_1_bit
Predictor_2Bit  = Predict_2_bit = Predictor_2_bits
Predictor_Never = Predictor_Never_taken
Predictor_Always = Predictor_Always_taken

PREDICTORS = {
    "never_taken":  Predictor_Never_taken,
    "always_taken": Predictor_Always_taken,
    "1_bit":        Predictor_1_bit,
    "2_bits":       Predictor_2_bits,
    "history":      Predictor_With_History,
    # Variantes en español y alias comunes
    "nunca":        Predictor_Never_taken,
    "siempre":      Predictor_Always_taken,
    "1bit":         Predictor_1_bit,
    "2bits":        Predictor_2_bits,
    "1_bit_dynamic": Predictor_1_bit,
    "2_bit_dynamic": Predictor_2_bits,
}


def get_predictor(name_or_class=None, **kwargs) -> BASE_PREDICTOR:
    """
    Función de fábrica para instanciar un predictor según nombre o clase.
    Por defecto devuelve Predictor_Never_taken si no se especifica.

    Ejemplos:
    - get_predictor("2_bits")
    - get_predictor("never_taken")
    - get_predictor(Predictor_1_bit)
    """
    if name_or_class is None:
        return Predictor_Never_taken(**kwargs)

    if isinstance(name_or_class, type) and issubclass(name_or_class, BASE_PREDICTOR):
        return name_or_class(**kwargs)

    key = str(name_or_class).strip().lower()
    if key in PREDICTORS:
        return PREDICTORS[key](**kwargs)

    raise ValueError(f"Predictor no reconocido: '{name_or_class}'. Opciones disponibles: {list(PREDICTORS.keys())}")
