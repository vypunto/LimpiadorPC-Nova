# Limpiador PC Nova (v4)

Optimizador, reparador y protector para Windows 10/11. Interfaz futurista local, sin telemetría y sin dependencias (Python 3.10+ estándar).

## Abrir
- **`dist/LimpiadorPC-Nova.exe`**: no necesita Python. La primera vez SmartScreen puede avisar (no está firmado): «Más información → Ejecutar de todas formas».
- O doble clic en **`iniciar.bat`** (se abre como ventana de app con Chrome/Edge). Para desbloquear todo: botón **Ejecutar como admin** dentro de la app.

## Secciones
| Sección | Qué hace |
|---|---|
| Panel | Salud 0-100, CPU/RAM en vivo, discos, procesos, recomendaciones y **Optimizar ahora** |
| Limpieza | Temporales, papelera, Windows Update, cachés de todos los perfiles de Chrome/Edge/Brave/Opera/Firefox, GPU (NVIDIA/AMD/DirectX), Discord, Steam, Spotify, npm/pip/yarn/Go/NuGet |
| Espacio | Archivos grandes, carpetas pesadas y archivos **sin usar** desde hace meses/años |
| Duplicados | Verificados por hash completo (BLAKE2), conserva el más antiguo |
| Seguridad | Defender: estado, análisis rápido/completo, firmas, historial + auditoría de inicio, tareas, hosts, proxy, UAC, firewall, exclusiones |
| Reparar | Punto de restauración, SFC, DISM, CHKDSK, Windows Update, Store, Explorador, iconos, audio, impresora, DNS, IP, red, hora, WinSxS, TRIM, planes de energía, hibernación |
| Salud | Apagados inesperados, BSOD, WHEA, minidumps, SMART, informe HTML |
| Inicio | Activar/desactivar reversible (como el Administrador de tareas) |
| Programas | Tamaño, sin uso, desinstalador oficial |
| Buscar | Búsqueda en tus carpetas |

## Extras
- **Limpieza automática semanal** (Limpieza → Automático): tarea de Windows sin permisos de admin, solo categorías seguras.
- **Historial** de todo lo limpiado, borrado o cambiado: botón en la barra lateral (`%LOCALAPPDATA%\LimpiadorPC\historial.log`).
- Recompilar el .exe: `py -3 tools/build_exe.py`

## Seguridad del diseño
- Antes de SFC, DISM, reset de Windows Update/red, etc. se crea un **punto de restauración** automáticamente.
- En unidades sin Papelera (USB, red) no se borra nada.
- Los archivos que borras van a la **Papelera** (recuperables); solo rutas mostradas por un análisis y nunca carpetas del sistema.
- Servidor solo en 127.0.0.1 con clave aleatoria por sesión.
- No “limpia” el registro ni toca documentos o programas sin tu confirmación.

La interfaz antigua (tkinter) está en `legacy/` solo como referencia.

## Desarrollo
- Dependencias: `py -3 -m pip install -r requirements.txt` (solo hacen falta para la IA y para compilar).
- Probar todo (33 comprobaciones seguras, no borra nada tuyo): `py -3 tools/prueba.py`
- Compilar el `.exe`: `py -3 tools/build_exe.py` → `dist/LimpiadorPC-Nova.exe`

## Soporte
Si algo falla: barra lateral → **Informe técnico** → Copiar o Guardar. Incluye versión, Windows y los últimos errores,
sin archivos ni claves y con el nombre de usuario anonimizado. Los errores se guardan en `%LOCALAPPDATA%\LimpiadorPC\errores.log`.
