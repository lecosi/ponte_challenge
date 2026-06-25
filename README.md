# Call Center Simulation

Simulación de un call center que distribuye tickets entre N agentes en paralelo y registra los tiempos de asignación y resolución en archivos CSV.

---

## Arquitectura

El sistema implementa un patrón **productor-consumidor** con una Queue controlada:

```
[CSV de entrada]
      │
      ▼
 TicketReader          Lectura, validación y ordenamiento por prioridad
      │
      ▼
  Simulation
      │
      ├─── Producer ──────► Queue (máx. 100 tickets) ◄─── backpressure
      │                           │
      │              ┌────────────┼────────────┐
      │              ▼            ▼            ▼
      │          Agent 1      Agent 2  ...  Agent N     (2–3s por ticket)
      │              │            │            │
      └──────────────▼────────────▼────────────▼
                  ResultWriter (escribe CSV de forma incremental)
```

### Componentes

| Archivo | Responsabilidad |
|---|---|
| `models/ticket.py` | Contenedor de datos del ticket. Inmutable durante la simulación; el estado se propaga retornando nuevas instancias |
| `models/agent.py` | Atiende tickets con un delay aleatorio de 2–3s y retorna una nueva instancia resuelta |
| `services/csv_reader.py` | Lee el CSV de entrada, valida cada fila y ordena por prioridad |
| `services/csv_writer.py` | Escribe resultados de forma incremental con flush cada 500 filas |
| `services/simulation_process.py` | Orquesta el flujo completo con `asyncio` |
| `main.py` | Entry point: parsea argumentos y ejecuta los casos de prueba |

---

## Decisiones de diseño

### `asyncio` sobre `threading`

La atención de un ticket es espera pura (`asyncio.sleep`), no trabajo de CPU. `asyncio` maneja esto con un único hilo y sin el overhead del GIL: mientras un agente espera, el event loop cede el control a otro. Con `threading` se pagaría el costo de context switching sin ningún beneficio real.

### Cola acotada con backpressure

La `asyncio.Queue` tiene un límite de 100 elementos. Cuando todos los agentes están ocupados, `await queue.put()` bloquea el productor hasta que se libera un slot. Esto mantiene el consumo de memoria constante independientemente del tamaño del CSV. Esto lo hice en caso de procesar miles o millones de registros.

### Copia lazy en el productor con `as_unassigned()`

En lugar de clonar toda la lista de tickets al inicio de cada simulación, se llama `as_unassigned()` justo antes de encolar cada ticket usando `dataclasses.replace()`. Esto separa los datos de entrada del estado de simulación (`agente`, `fecha_asignacion`, `fecha_resolucion`), garantizando que la misma lista pueda reutilizarse para los tres casos de prueba. Por lo cual, solo existen 100 copias vivas en memoria.

### Escritura incremental sin lock

`ResultWriter` escribe al CSV inmediatamente después de cada solucion de ticket. No requiere `asyncio.Lock` porque `asyncio` es monohilo: `csv.writer.writerow()` es síncrono y no puede ser interrumpido por otra corrutina. El flush ocurre cada 500 filas(este es un numero que consideré por experiencia pero puede ajustarse) para evitar un syscall por ticket sin sacrificar durabilidad.

### Validación con excepción interna `_InvalidRow`

La validación en `TicketReader` usa `_InvalidRow` cuando la fila es inválida. Las filas inválidas se registran como `WARNING` y el procesamiento continúa sin interrupciones.

### Ordenamiento previo a la simulación

Los tickets se ordenan una sola vez antes de entrar a la cola (prioridad ascendente, luego fecha de creación). Como la cola es FIFO y los tickets ya llegan ordenados, se preserva la secuencia correcta sin necesidad de una `PriorityQueue` dentro de la simulación.

### Timestamps con fecha completa

En la prueba, en el ejemplo de los archivos de respuesta se ve la `fecha_asignacion` y `fecha_resolucion` solo como hora (`08:00:02`). En este caso uso el datetime completo (`2026-06-23 10:00:02`) porque una simulación puede arrancar cerca de la medianoche y cruzarla — perder la fecha haría los datos ambiguos. El formato es `%Y-%m-%d %H:%M:%S`.
---

## Estructura del proyecto

```
ponte_challenge/
├── call_center/
│   ├── __init__.py
│   ├── files/
│   │   └── tickets_dataset.csv
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── ticket.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_reader.py
│   │   ├── csv_writer.py
│   │   └── simulation_process.py
│   └── tests/
│       ├── __init__.py
│       ├── test_agent.py
│       ├── test_csv_reader.py
│       ├── test_csv_writer.py
│       ├── test_simulation.py
│       └── test_ticket.py
├── main.py
├── pytest.ini
├── test_requirements.txt
└── README.md
```

---

## Requisitos

- Python 3.9+ (actualmente estoy usando la 3.14.3)

```bash
pip install -r test_requirements.txt
```

---

## Ejecución

```bash
# Casos por defecto: 3, 5 y 7 agentes
python3 main.py call_center/files/tickets_dataset.csv

# Número de agentes personalizado
python3 main.py call_center/files/tickets_dataset.csv --agents 4 8
```

Los resultados se generan en `output/`:

```
output/
├── result_agents_3.csv
├── result_agents_5.csv
└── result_agents_7.csv
```

**Formato del CSV de salida:**

```
id,fecha_creacion,prioridad,agente,fecha_asignacion,fecha_resolucion
5,2024-01-01 08:00:00,1,2,2026-06-23 10:00:00,2026-06-23 10:00:02
```

---

## Tests

```bash
# Todos los tests
pytest -v

# Un archivo específico
pytest call_center/tests/test_csv_reader.py -v
```

| Test | Qué cubre |
|---|---|
| `test_ticket.py` | Estado del ticket, `as_unassigned()`, ordenamiento |
| `test_csv_reader.py` | CSV válido, archivo no encontrado, 10 tipos de fila inválida, ordenamiento |
| `test_agent.py` | Atención de ticket, inmutabilidad del original, timestamps, contador |
| `test_csv_writer.py` | Ciclo de vida del archivo, contenido del CSV, validaciones |
| `test_simulation.py` | Integración: tickets resueltos, CSV correcto, originales sin mutar |

