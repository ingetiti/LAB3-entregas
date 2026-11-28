; JSR y RET: R0 queda en 9.
.ORIG x3000
    AND R0, R0, #0
    ADD R0, R0, #3
    JSR TRIPLE
    HALT
TRIPLE ADD R1, R0, R0
    ADD R0, R1, R0
    RET
.END
