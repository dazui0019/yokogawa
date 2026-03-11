# IMDLM3054-17EN summary

Source files:
- `IMDLM3054-17EN-command-index.txt`: fastest way to locate a command group or page.
- `IMDLM3054-17EN-ch5-commands.txt`: detailed command descriptions and examples.
- `IMDLM3054-17EN.txt`: full extracted manual including programming rules in chapter 4.

## What this manual is

This is the communication interface manual for Yokogawa DLM3022/3024/3032/3034/3052/3054 scopes.
For automation work, the most important parts are:

- Chapter 4: SCPI message syntax, response rules, data types, and synchronization.
- Chapter 5.1: command index.
- Chapter 5.2 to 5.38: per-command details.

The command index contains 37 top-level groups. Many are feature-specific. For normal remote control, only a subset matters day to day.

## SCPI rules you will actually use

- Query commands end with `?`, for example `:TIMebase?` or `*IDN?`.
- Set commands are `HEADER <space> DATA`, for example `:ACQuire:MODE NORMal`.
- Multiple commands can be concatenated with `;`.
- After sending a query, read the full response before sending the next command, or the scope can raise an error.
- Keep a single program message below about 1024 bytes to avoid deadlock risk.
- Command headers are case-insensitive and can use long or short forms.
  Example: `:TRIGger:MODE` and `:TRIG:MODE`.
- Boolean parameters usually accept `ON|OFF` or `1|0`.
- Binary waveform transfers use block-data format (`#<digits><byte-count><payload>`).

## Synchronization and reliability

These commands are the foundation of stable automation:

- `*IDN?`: identify instrument model, serial, firmware.
- `*RST`: reset settings.
- `*CLS`: clear status and error queue.
- `:STATus:ERRor?`: read the next queued error.
- `*OPC?`: wait until an overlap operation completes and then return `1`.
- `*WAI`: block later commands until the selected overlap command completes.
- `:COMMunicate:OPSE`: choose which overlap command `*OPC`, `*OPC?`, and `*WAI` apply to.
- `:COMMunicate:HEADer`: choose whether query responses include headers.
- `:COMMunicate:VERBose`: choose long-form or short-form response text.

Practical rule: for scripts, prefer `*CLS` before a sequence, `*OPC?` around slow or overlapping operations, and `:STATus:ERRor?` when debugging.

## Most important command groups

### 1. `ACQuire Group`

Controls how data is acquired.

- `:ACQuire:MODE`
- `:ACQuire:AVERage:COUNt`
- `:ACQuire:COUNt`
- `:ACQuire:RESolution`
- `:ACQuire:RLENgth`
- `:ACQuire:SAMPling`

Use this group to decide normal vs averaging capture, record length, and sampling behavior.

### 2. `CHANnel Group`

Controls the analog input channels.

- `:CHANnel<x>:COUPling`
- `:CHANnel<x>:BWIDth`
- `:CHANnel<x>:DISPlay`
- `:CHANnel<x>:OFFSet`
- `:CHANnel<x>:POSition`
- `:CHANnel<x>:PROBe[:MODE]`
- `:CHANnel<x>:VDIV`
- `:CHANnel<x>:VARiable`

This is the group you use to make the waveform readable before triggering or measurement.

### 3. `TIMebase Group`

Controls the horizontal scale.

- `:TIMebase:TDIV`
- `:TIMebase:SRATe?`

In practice, `TDIV` and acquisition record length together largely determine capture duration and resolution.

### 4. `TRIGger Group`

Controls when a capture occurs. This group is very large because it also covers advanced serial-bus triggers.

Core trigger commands to learn first:

- `:TRIGger:MODE`
- `:TRIGger:POSition`
- `:TRIGger:SCOunt`
- `:TRIGger:SOURce:CHANnel<x>:LEVel`
- `:TRIGger:SOURce:CHANnel<x>:HFRejection`
- `:TRIGger:SOURce:CHANnel<x>:NREJection`

If you only need ordinary edge-style automation, start with trigger mode, position, source channel, and level. Leave CAN/LIN/I2C/SPI/UART trigger trees for later.

### 5. `MEASure Group`

Controls automatic measurements and statistics.

Important patterns:

- `:MEASure:{CHANnel<x>|MATH<x>}:<Parameter>:STATe`
- `:MEASure:{CHANnel<x>|MATH<x>}:<Parameter>:VALue?`
- `:MEASure:{CHANnel<x>|MATH<x>}:<Parameter>:{MAXimum|MEAN|MINimum|SDEViation}?`
- `:MEASure:{CHANnel<x>|MATH<x>}:ALL`
- `:MEASure:{CHANnel<x>|MATH<x>}:DELay...`

This group is broad. The mental model is:

- enable a measurement item,
- query its current value,
- optionally query statistics,
- optionally configure inter-channel delay measurement.

### 6. `WAVeform Group`

Used to retrieve raw waveform samples. This is the most important group for programmatic data export.

Core workflow:

1. Select source with `:WAVeform:TRACe`
2. Select format with `:WAVeform:FORMat`
3. Optionally set `:WAVeform:STARt` and `:WAVeform:END`
4. Query scale metadata:
   - `:WAVeform:RANGe?`
   - `:WAVeform:OFFSet?`
   - `:WAVeform:SRATe?`
   - `:WAVeform:TRIGger?`
5. Fetch samples with `:WAVeform:SEND?`

High-value commands:

- `:WAVeform:FORMat {ASCii|BYTE|RBYTe|WORD}`
- `:WAVeform:LENGth?`
- `:WAVeform:RECord`
- `:WAVeform:STARt`
- `:WAVeform:END`
- `:WAVeform:SEND?`
- `:WAVeform:ALL:SEND?`

Important caveats from the manual:

- waveform query is not available in `Single` or `NSingle` trigger mode,
- waveform query is not available in roll mode,
- binary transfer needs conversion using range, offset, position, and format rules.

### 7. `STATus Group`

Used for event tracking and debugging.

- `:STATus:CONDition?`
- `:STATus:EESE`
- `:STATus:EESR?`
- `:STATus:ERRor?`
- `:STATus:FILTer<x>`

Use this when a command sequence behaves unexpectedly or when coordinating long-running operations.

### 8. `FILE Group`

Used to load and save files on the instrument or attached storage.

- `:FILE:SAVE...`
- `:FILE:LOAD...`
- `:FILE:MOVE...`
- `:FILE:REName`
- `:FILE:PROTect`

Useful when you want the scope itself to save waveform, setup, screenshot, FFT, or measurement outputs.

## Specialist groups worth knowing exist

These groups are powerful but usually not part of the first automation pass:

- `ANALysis`
- `FFT`
- `HISTory`
- `LOGic`
- `MATH`
- `SEARch`
- `SERialbus`
- `WPARameter`
- `XY`
- `ZOOM`
- `GONogo`
- `HCOPy`
- `IMAGe`
- `REFerence`
- `STORe`
- `SYSTem`

Serial-bus support is especially deep. If the project later needs CAN, CAN FD, I2C, SPI, UART, LIN, SENT, FlexRay, or PSI5 features, the relevant commands already exist, but they are not worth summarizing in detail until needed.

## Suggested working order for future scripting

If the goal is "connect, configure, capture, and read back data", use this order:

1. `*IDN?`
2. `*CLS`
3. Channel setup: `:CHANnel...`
4. Timebase setup: `:TIMebase...`
5. Acquisition setup: `:ACQuire...`
6. Trigger setup: `:TRIGger...`
7. Start or wait for acquisition
8. Read measurements with `:MEASure...` or samples with `:WAVeform...`
9. Check `:STATus:ERRor?` if anything looks wrong

## Fast lookup tips

- Need voltage scale or coupling: search `CHANnel`.
- Need capture depth or averaging: search `ACQuire`.
- Need trigger point or trigger mode: search `TRIGger`.
- Need measurement values: search `MEASure`.
- Need raw samples: search `WAVeform`.
- Need completion/status handling: search `*OPC?`, `*WAI`, `STATus`, `COMMunicate`.

## Bottom line

For this project, the minimal core is:

- `*IDN?`, `*CLS`, `*OPC?`, `:STATus:ERRor?`
- `:CHANnel<x>:VDIV`, `:CHANnel<x>:OFFSet`, `:CHANnel<x>:COUPling`
- `:TIMebase:TDIV`
- `:ACQuire:MODE`, `:ACQuire:RLENgth`
- `:TRIGger:MODE`, `:TRIGger:POSition`, trigger source/level commands
- `:MEASure...:VALue?`
- `:WAVeform:FORMat`, `:WAVeform:TRACe`, `:WAVeform:SEND?`

Everything else can be pulled in on demand.
