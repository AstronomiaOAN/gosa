import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def modify_html(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add body class if not present
    if '<body class="lang-es">' not in content:
        content = content.replace('<body>', '<body class="lang-es">')

    # Replace specific text nodes with spans
    translations = {
        '>Inicio<': '><span class="es">Inicio</span><span class="en">Home</span><',
        '>Acerca de<': '><span class="es">Acerca de</span><span class="en">About Us</span><',
        '>Novedades<': '><span class="es">Novedades</span><span class="en">News</span><',
        '>Investigación<': '><span class="es">Investigación</span><span class="en">Research</span><',
        '>Integrantes<': '><span class="es">Integrantes</span><span class="en">Team</span><',
        '>Producción<': '><span class="es">Producción</span><span class="en">Production</span><',
        '>Contacto<': '><span class="es">Contacto</span><span class="en">Contact</span><',
        '>Colaboraciones<': '><span class="es">Colaboraciones</span><span class="en">Collaborators</span><',
        '>Enlaces Rápidos<': '><span class="es">Enlaces Rápidos</span><span class="en">Quick Links</span><',
        '>Acerca de nosotros<': '><span class="es">Acerca de nosotros</span><span class="en">About Us</span><',
        '>Equipo<': '><span class="es">Equipo</span><span class="en">Team</span><',
        '>Síguenos<': '><span class="es">Síguenos</span><span class="en">Follow Us</span><',
        '>Grupo de Astrofísica Solar<': '><span class="es">Grupo de Astrofísica Solar</span><span class="en">Solar Astrophysics Group</span><',
        '>Observatorio Astronómico Nacional<br>Universidad Nacional de Colombia<': '><span class="es">Observatorio Astronómico Nacional<br>Universidad Nacional de Colombia</span><span class="en">National Astronomical Observatory<br>National University of Colombia</span><',
        '&copy; 2024 Grupo de Astrofísica Solar (GoSA). Todos los derechos reservados.': '&copy; 2024 <span class="es">Grupo de Astrofísica Solar (GoSA). Todos los derechos reservados.</span><span class="en">Solar Astrophysics Group (GoSA). All rights reserved.</span>'
    }

    for es_text, dual_text in translations.items():
        if dual_text not in content: # prevent double replacement
            content = content.replace(es_text, dual_text)

    # Insert the lang switcher in the navbar
    nav_item_close = '<li><a href="#colaboraciones" class="nav-link"><span class="es">Colaboraciones</span><span class="en">Collaborators</span></a></li>'
    nav_item_close2 = '<li><a href="index.html#colaboraciones" class="nav-link"><span class="es">Colaboraciones</span><span class="en">Collaborators</span></a></li>'
    
    lang_switcher = """
                <li class="lang-switcher">
                    <button class="lang-toggle-btn active" onclick="setLang('es')" id="btn-es">ES</button>
                    <span style="color:var(--text-muted)">|</span>
                    <button class="lang-toggle-btn" onclick="setLang('en')" id="btn-en">EN</button>
                </li>
"""
    
    if 'class="lang-switcher"' not in content:
        if nav_item_close in content:
            content = content.replace(nav_item_close, nav_item_close + lang_switcher)
        elif nav_item_close2 in content:
            content = content.replace(nav_item_close2, nav_item_close2 + lang_switcher)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    modify_html(os.path.join(REPO_ROOT, "index.html"))
    modify_html(os.path.join(REPO_ROOT, "produccion.html"))
