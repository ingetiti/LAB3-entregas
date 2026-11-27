; SUMOVER: R0 = (A + B + C) mod 65536; R2 = carry de salida.
; Entrada: A en R0, B en R1 y C en R2 (0 o 1).
; Conserva los registros del llamador y el NZP heredado, que refleja R4.
SUMOVER
    LSR R2, R2, #1
    ADC R0, R0, R1
    ADC R2, R2, R2
    ADD R4, R4, #0
    RET
.END
