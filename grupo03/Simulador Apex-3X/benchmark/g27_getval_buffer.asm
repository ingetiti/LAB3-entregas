
;
; Buffer compartido entre las subrutinas de esta carpeta
; [LC-3X — adaptada]
;
; Cambios:
;   En LC-3X la memoria es byte-addressable.
;   El buffer almacena 1 caracter por BYTE.
;   Para guardar 32 caracteres + nulo necesitamos 32+1 = 33 bytes.
;   .BLKW #17 = 34 bytes (17 palabras de 2 bytes) -> suficiente.
;   BUFFER_END apunta al byte inmediatamente posterior al ultimo byte del buffer.
;   getline usa STBL para escribir de a un byte.

BUFFER      .BLKW #17       ; 34 bytes para hasta 33 chars + '\0'
BUFFER_END  .FILL #0        ; centinela (nunca se escribe aqui)

.END
