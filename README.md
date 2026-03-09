# WaveBox

**WaveBox** es un laboratorio visual para estudiar propagación ondulatoria en dos dimensiones sobre medios heterogéneos. El programa integra en tiempo real una ecuación de onda escalar con amortiguamiento, potencial espacial, variación local de velocidad e inclusión de obstáculos duros. Su propósito es pedagógico, experimental y abierto: servir como motor base para explorar fenómenos ondulatorios, leer código numérico, crear presets propios y extender el sistema hacia otros modelos físicos.

## Qué modela

WaveBox evoluciona un campo escalar $u(x,y,t)$ según

$$
\frac{\partial^2 u}{\partial t^2} + \gamma \, \frac{\partial u}{\partial t}
= \nabla \cdot \big(c(x,y)^2 \, \nabla u\big) - V(x,y)\,u.
$$

Aquí:

- $u(x,y,t)$ es la amplitud de una onda escalar bidimensional.
- $c(x,y)$ controla la velocidad local de propagación. Cuando cambia en el espacio, aparecen efectos análogos a refracción.
- $V(x,y)$ actúa como un paisaje de potencial/dispersión que modifica la evolución local del campo.
- $\gamma$ introduce amortiguamiento.
- Los obstáculos duros se implementan imponiendo $u=0$ dentro de una máscara espacial.

El programa permite observar, en una misma plataforma, reflexión, transmisión parcial, difracción, guiado, dispersión por potenciales, refracción efectiva y efectos geométricos asociados a regiones estructuradas del plano.

## Qué no modela

WaveBox **no** resuelve, en esta release, la ecuación de Schrödinger, las ecuaciones de Maxwell ni ecuaciones de ondas gravitacionales. Algunas lecturas visuales pueden ser útiles como analogías pedagógicas, pero no deben confundirse con una equivalencia formal exacta.

Dicho de otra manera: el programa es un motor de **onda escalar 2D**. Su valor está en que acerca ideas de física teórica, EDPs y cálculo numérico a una observación gráfica manipulable, no en fingir que ya resuelve todos los modelos ondulatorios de la física matemática.

## Por qué el cálculo numérico aquí sí importa

La gracia del proyecto no está solo en “ver algo bonito moverse”. Está en que una ecuación diferencial parcial, discretizada con cuidado, puede transformarse en un objeto interactivo que deja tocar sus parámetros, observar regímenes distintos y construir intuición física.

En esta implementación se usa, de forma general:

- discretización explícita en el tiempo para la evolución del campo;
- diferencias finitas espaciales para aproximar $\nabla \cdot (c^2 \nabla u)$;
- promediado en caras para el campo $c^2$, con el fin de tratar mejor medios no homogéneos;
- bordes absorbentes y variantes reflectantes según el modo elegido;
- máscaras duras para representar paredes y barreras geométricas;
- exportación de video recalculando la dinámica cuadro a cuadro.

El resultado no reemplaza un curso serio de métodos numéricos, pero sí permite ver con mucha claridad por qué la computación científica es una extensión natural del trabajo teórico.

## Características principales

- interfaz Qt interactiva;
- simulación en tiempo real;
- presets geométricos, refractivos, periódicos, polares y pixel-art;
- presets con parámetros sugeridos y condición inicial sugerida;
- opción para conservar o no los parámetros actuales al cambiar preset;
- temas visuales para la interfaz y para la simulación;
- monitoreo de FPS, RAM y VRAM cuando el sistema lo permite;
- exportación MP4 de un preset único o de una mezcla de hasta 5 tramos;
- memoria local simple para recordar la última configuración útil.

## Presets incluidos

La release pública **v0.30.0** incluye 21 presets:

- 8-bit ghost
- 8-bit Mega Man
- Red cristalina de dispersores
- Nube aleatoria de dispersores
- Dúo de cilindros suaves
- Doble rendija dura
- Rendija única
- Anillo reflectante
- Guía de onda plana
- Laberinto realista
- Damero refractivo
- Lente gaussiana
- Potencial cosenoidal 2D
- Yukawa central
- Potencial corazón
- Rosa polar de 4 pétalos
- Rosa polar de 6 pétalos
- Cardioide polar
- Lemniscata polar
- Estrella polar de 8 lóbulos
- Corona polar de 12 sectores

La idea no es solo “usar” estos presets, sino tomarlos como material base para inventar otros: medios periódicos, regiones desordenadas, perfiles radiales, barreras múltiples, sprites, potenciales inspirados en apuntes, o incluso pruebas numéricas más ambiciosas.

## Instalación

### Requisitos

- Python 3.10 o superior
- `ffmpeg` recomendado para exportación de video

### Dependencias de Python

```bash
pip install -r requirements.txt
```

### Ejecutar

```bash
python wavebox.py
```

## Dependencias

Las dependencias incluidas en `requirements.txt` son:

- `numpy`
- `opencv-python`
- `PyQt6`
- `pyqtgraph`
- `psutil`

Si `ffmpeg` está disponible en tu `PATH`, WaveBox lo usará para generar MP4 con mejor compatibilidad. Si no está disponible, el programa intenta usar OpenCV como plan B.

## Uso rápido

1. Elige un preset.
2. Decide si quieres aplicar o no los ajustes sugeridos del preset.
3. Ajusta borde, potencial, índice efectivo, amortiguamiento y calidad visual.
4. Observa el mapa superpuesto adecuado:
   - potencial de dispersión;
   - obstáculos sólidos;
   - índice de refracción efectivo.
5. Exporta un video único o una mezcla secuencial de hasta 5 tramos.

## Qué conviene mirar al usarlo

- **Doble rendija / rendija única**: difracción e interferencia.
- **Damero refractivo / lente gaussiana**: curvatura del frente y cambio de dirección por medio no homogéneo.
- **Yukawa central**: dispersión localizada de corto alcance.
- **Guía de onda / laberinto**: canalización, rebotes múltiples y tiempos de recorrido.
- **Presets polares**: cómo una geometría con simetría discreta deja su firma sobre la evolución del frente.
- **Presets pixel-art**: cómo una estructura espacial discreta produce una respuesta ondulatoria con huella geométrica clara.

## Ruta sugerida para estudiar la teoría

WaveBox se disfruta más cuando se lo usa junto con teoría. Una ruta razonable sería:

1. ecuación de ondas clásica y condiciones de borde;
2. diferencias finitas y estabilidad numérica;
3. refracción y medios no homogéneos;
4. dispersión por potenciales y obstáculos;
5. lectura crítica de analogías con mecánica cuántica, electromagnetismo y otras teorías ondulatorias.

## Bibliografía recomendada

### Ondas, óptica y electromagnetismo

- David J. Griffiths, *Introduction to Electrodynamics*.
- Eugene Hecht, *Optics*.
- John David Jackson, *Classical Electrodynamics*.

### Métodos matemáticos y numéricos

- George B. Arfken, Hans J. Weber, Frank E. Harris, *Mathematical Methods for Physicists*.
- Randall J. LeVeque, *Finite Difference Methods for Ordinary and Partial Differential Equations*.
- Richard Haberman, *Applied Partial Differential Equations*.

### Recursos abiertos para partir

- OpenStax — *University Physics, Volume 3*: https://openstax.org/details/books/university-physics-volume-3
- MIT OpenCourseWare — Vibrations and Waves: https://ocw.mit.edu
- David Tong — lecture notes: https://www.damtp.cam.ac.uk/user/tong/teaching.html

## Hacia dónde puede crecer

Esta release es deliberadamente una base. Algunas extensiones naturales serían:

- evolución tipo Schrödinger para funciones de onda complejas;
- propagación electromagnética en 2D con polarizaciones explícitas;
- medios dispersivos o anisótropos más realistas;
- acoplo con potenciales dependientes del tiempo;
- mejores condiciones absorbentes;
- análisis espectral y herramientas de diagnóstico más finas;
- exploración de modelos linealizados de ondas gravitacionales como etapa posterior y conceptualmente distinta.

## Sobre IA y autoría

Este proyecto es también un experimento sobre los límites de lo que puede hacerse con ChatGPT 5.2–5.4 Thinking en tareas de simulación física y computación numérica, con el enfoque de aproximar la física teórica a la observación gráfica de sus modelos en el tiempo mediante simulaciones en tiempo real hechas con IA.

Se usaron prompts de ingeniería inversa para pedirle a la IA que reconstruyera simulaciones inspiradas en videos de este tipo. Después vino lo importante: estudiar críticamente lo que generaba, corregirlo, ampliarlo, pedir nuevas funciones, ajustar presets, mejorar la interfaz, añadir exportación de video y volver a probar. La IA escribió mucho; el criterio físico, la lectura, la corrección y la decisión sobre qué conservar y qué descartar siguieron siendo humanos.

> Yo soy solo el mono detrás de la máquina de escribir que, por suerte del infinito, escribió el Quijote; salvo que no he escrito el Quijote, ni he escrito el código del programa. Que como buen quijote perisuge molinos de viento esperando el favor de Dulcinea, ¿no es cierto, Sancho?.

La invitación final es simple: exploren la IA con responsabilidad, pero sin miedo.

## Cómo contribuir

Si quieres aportar, revisa `CONTRIBUTING.md`. Las contribuciones más naturales para este proyecto son:

- nuevos presets;
- mejoras numéricas;
- mejor documentación;
- validación física más fina;
- nuevas exportaciones y herramientas visuales;
- corrección de bugs.

## Licencia

Este proyecto se distribuye bajo licencia **MIT**. Revisa `LICENSE`.
