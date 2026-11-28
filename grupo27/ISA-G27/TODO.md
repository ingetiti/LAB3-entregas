### LISTA DE TODO (DE ULTRA BAJA PRIORIDAD -hacer solo si sobra tiempo y tokens-)

- [ ] Cambiar el modo de retorno desde llamadas al sistema *TRAP* para que no utilice R7 como si fuese una subrutina. En lugar de eso se podría guardar en la pila un dato extra que sea el PC de retorno.

- [ ] Rehacer el sistema operativo, pero en vez de tener dos instrucciones especializadas del propio simulador, implementar interrupciones, tabla de interrupciones, controladores de interrupciones, memoria mapeada de dispositivos (KBSR, KBDR, DSR, DDR) (MCR tendrá de bit 15 al *clock enable*, que se pone en 0 al llamar a HALT, y de bit 14 tendrá a *wait for interrupt*, que detendrá el reloj hasta que ocurra una interrupción como cuando se pulsa una tecla, de esta forma GETC no necesitara hacer *bussy waiting*, sino que simplemente esperara la interrupción)

- [ ] Implementar un modulo aparte que se pueda aprovechar usando *Ducktyping* que sea *debugger*, que se pueda utilizar desde dentro del simulador para ir paso a paso, inspeccionar un rango de instrucciones, inspeccionar registros, inspeccionar memoria, inspeccionar *breakpoints*, cambiar valores durante la ejecución, pausar, continuar, paso siguiente, paso ingresante, etc.

- [ ] Implementar predictores de salto de *forward never taken* (nunca delante, siempre atrás), *forward always taken* (siempre adelante, nunca atrás), *buffered 1 bit* (con historial, 1 bit) y *buffered 2 bits* (con historial, 2 bits).

- [ ] Aplicación con GUI para trabajar con una interfaz y no desde la consola.
