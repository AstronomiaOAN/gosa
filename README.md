# Documentación del Proyecto Web GOSA

Este repositorio contiene el código fuente de la página web del **Grupo de Observación Solar y Astrofísica (GOSA)**. La página está construida utilizando tecnologías web estándar (Vanilla HTML, CSS y JavaScript) sin dependencias externas pesadas, garantizando un rendimiento óptimo y un mantenimiento sencillo.

## 📂 Estructura del Proyecto

El proyecto está dividido en varios archivos principales que separan la estructura, el diseño y la lógica:

- **`index.html`**: Página principal del grupo. Contiene secciones de inicio, sobre nosotros, líneas de investigación, equipo y contacto.
- **`produccion.html`**: Página dedicada a mostrar las publicaciones científicas y tesis (de pregrado, maestría y doctorado) del grupo, con funcionalidades de filtrado.
- **`dynasun.html`**: Página específica para el proyecto Dynasun.
- **`styles.css`**: Hoja de estilos principal. Contiene todas las reglas de diseño, variables CSS para los colores, estilos de fuente, diseño responsivo y animaciones.
- **`script.js`**: Archivo principal de lógica del cliente. Maneja la interactividad de la página, animaciones al hacer scroll, filtros y la internacionalización (cambio de idioma).
- **`Media/` e `images/`**: Carpetas que contienen los recursos visuales, imágenes de fondo, fotografías de los miembros del equipo y logotipos.
- **`data/`**: Archivos de datos fuente de las publicaciones (`publicaciones_organizadas.csv` y `publicaicones.txt`).
- **`docs/`**: Documentos de referencia del grupo (p. ej. `Tesis de Maestría.txt`).
- **`scripts/`**: Scripts auxiliares de mantenimiento (p. ej. `translate_html.py`, usado puntualmente para inyectar el selector de idioma en el HTML).
- **`archive/`**: Archivos sueltos sin uso actual en el sitio, conservados por si acaso (fotos sin referenciar, un duplicado, un archivo `.enc`).

---

## ⚙️ Funcionamiento del Código y Lógica (`script.js`)

El archivo `script.js` es el corazón interactivo de la página. Todo su código inicial se ejecuta una vez que el DOM ha cargado completamente (`DOMContentLoaded`). A continuación, se explican sus funciones principales:

### 1. Generador de Estrellas (`generateStars`)
```javascript
const generateStars = (id, count) => { ... }
```
Genera un efecto visual de fondo estrellado calculando posiciones `(x, y)` aleatorias a lo largo del ancho y alto de la ventana, y utilizando la propiedad `box-shadow` CSS para renderizarlas de manera eficiente en contenedores específicos (`stars`, `stars2`, `stars3`).

### 2. Animaciones al Hacer Scroll (Intersection Observer)
Utiliza la API `IntersectionObserver` para detectar cuándo un elemento con la clase `.scroll-appear` entra en el campo de visión del usuario. Al detectarlo, le añade la clase `visible` para activar animaciones CSS (como un "fade-in"), haciendo que el sitio se sienta dinámico a medida que el usuario baja por la página.

### 3. Manejo de Navegación y Scroll (`handleScroll`)
- **Header dinámico**: Añade una clase `.scrolled` al encabezado cuando el scroll baja más de 50px (para hacerlo más opaco o cambiar su tamaño).
- **Navegación Activa**: Detecta en qué sección de la página se encuentra el usuario y resalta automáticamente el enlace correspondiente en la barra de navegación.

### 4. Menú para Dispositivos Móviles
Escucha los eventos de clic en el botón tipo "hamburguesa" (`#menu-btn`) y alterna la clase `.open` en la barra de navegación para mostrar u ocultar las opciones en dispositivos de pantallas pequeñas.

### 5. Cambio de Pestañas (Tabs)
Maneja la lógica para alternar entre diferentes paneles (por ejemplo, en secciones que tienen información separada por pestañas). Al hacer clic en un botón (`.tab-btn`), remueve las clases activas del resto y activa únicamente el panel correspondiente.

### 6. Sistema de Filtros (Equipo, Publicaciones y Tesis)
La página cuenta con una sólida lógica de filtrado visual:
- **Equipo**: Filtra las tarjetas de los miembros (`.team-member-card`) según el filtro seleccionado (ej. Todos, Estudiantes, Investigadores) agregando o removiendo la clase `.hidden`.
- **Publicaciones (`pubYearFilter`)**: Filtra la lista de publicaciones verificando si el atributo `data-year` coincide con el año seleccionado.
- **Tesis (`applyTesisFilters`)**: Un sistema de filtro combinado que permite buscar tesis tanto por año (`tesis-year-filter`) como por director de tesis (`tesis-dir-filter`).

### 7. Sistema de Internacionalización (Cambio de Idiomas)
```javascript
window.setLang = function (lang) { ... }
```
El sitio es bilingüe (Español / Inglés).
- **Lógica**: Cambia dinámicamente el idioma reemplazando las clases `.lang-es` o `.lang-en` en la etiqueta `<body>`. Mediante CSS, se controla qué textos se ocultan y cuáles se muestran dependiendo de esta clase global.
- **Persistencia**: El idioma preferido por el usuario se guarda en el almacenamiento local del navegador (`localStorage.setItem('gosa_lang', lang)`), asegurando que el idioma se mantenga al navegar entre páginas o al volver al sitio en el futuro.
- **Formularios**: Actualiza el texto de prueba (`placeholder`) en las entradas de texto según el idioma actual.

---

## 🎨 Aspectos de Estilos (`styles.css`)

El archivo CSS hace uso intensivo de:
- **Variables CSS (`:root`)** para definir paletas de colores, gradientes interactivos y sombras, lo que facilita cambiar la temática visual global en un futuro.
- **Flexbox y CSS Grid** para la creación de diseños completamente adaptables a dispositivos móviles (Responsive Design).
- **Transiciones y Keyframes** para los efectos `hover` sutiles en los botones y las animaciones de las partículas y el sol (Dynasun).
- Ocultamiento gestionado de idioma mediante pseudo-clases y clases del `body` (ej: `body.lang-en .es { display: none; }`).

## 🚀 Cómo ejecutar o trabajar en el proyecto localmente

1. Clona este repositorio:
   ```bash
   git clone <url-del-repositorio>
   ```
2. Al no usar un framework, no requiere instalación mediante `npm` ni procesos de compilación (build scripts).
3. Simplemente puedes abrir el archivo `index.html` en cualquier navegador web moderno, o si cuentas con VSCode, utilizar la extensión **Live Server** para previsualizar los cambios en tiempo real.
