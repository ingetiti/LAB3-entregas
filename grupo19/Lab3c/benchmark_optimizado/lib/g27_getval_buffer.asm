;
;   Buffer compartido entre las subrutinas de esta carpeta
;   En memoria direccionable por byte, cada caracter ocupa 1 byte (.BLKB).
;

BUFFER          .BLKB #32               ; 32 bytes para cadena de caracteres
BUFFER_END      .FILL #0                ; Centinela / fin del buffer (alineado a palabra par)

.END
