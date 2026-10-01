import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_site
from scripts.content import render_page, render_record
from scripts.site_assets import collect_assets, css_urls
from scripts.validate_site import validate


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        with patch.object(build_site, 'OUT', cls.root), contextlib.redirect_stdout(io.StringIO()):
            # main reports a project-relative output path; use individual build stages here.
            (cls.root / 'en').mkdir()
            for page in build_site.PAGES:
                for lang in build_site.LANGS:
                    target = cls.root / ('en' if lang == 'en' else '') / page
                    target.write_text(build_site.build_page(page, lang))
            (cls.root / 'sitemap.xml').write_text(build_site.build_sitemap())
            import shutil
            pages = {page: render_page(page) for page in build_site.PAGES}
            cls.assets = collect_assets(build_site.ROOT, pages)
            for asset in cls.assets:
                dest = cls.root / asset.relative_to(build_site.ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, dest)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_generated_site_is_valid(self):
        validate(self.root)

    def assert_invalid_edit(self, original, replacement, message):
        path = self.root / 'index.html'
        text = path.read_text()
        self.assertIn(original, text)
        try:
            path.write_text(text.replace(original, replacement, 1))
            with self.assertRaisesRegex(ValueError, message):
                validate(self.root)
        finally:
            path.write_text(text)

    def test_broken_asset_fails(self):
        self.assert_invalid_edit('src="Media/logo Gosa.avif"', 'src="images/missing.png"', 'missing target')

    def test_broken_anchor_fails(self):
        self.assert_invalid_edit('href="#inicio"', 'href="#missing"', 'missing anchor')

    def test_duplicate_id_fails(self):
        self.assert_invalid_edit('id="stars2"', 'id="stars"', 'duplicate IDs')

    def test_language_metadata_fails(self):
        self.assert_invalid_edit('hreflang="en"', 'hreflang="fr"', 'invalid hreflang en')

    def test_cross_language_navigation_fails(self):
        self.assert_invalid_edit('href="produccion.html"', 'href="en/produccion.html"', 'navigation changes language')

    def test_plain_data_is_escaped(self):
        html = render_record('member', dict(name='A < B "C"', category='investigador', image='x.png',
                                          role_html='<span>Role</span>', institution_html='', links_html=''))
        self.assertIn('A &lt; B &quot;C&quot;', html)
        self.assertIn('<span>Role</span>', html)

    def test_css_paths_with_spaces(self):
        self.assertEqual(css_urls('a{background:url("Media/imagen fondo.jpg")} b{background:url(../x.png)}'),
                         ['Media/imagen fondo.jpg', '../x.png'])

    def test_unused_originals_are_not_published(self):
        published = {str(path.relative_to(build_site.ROOT)) for path in self.assets}
        self.assertNotIn('images/macha_doble.gif', published)
        self.assertNotIn('images/Carlos Martinez.png', published)
        self.assertIn('images/video-optimized/mancha-solar.mp4', published)
        self.assertIn('Media/imagen sol.jpg', published)  # Social sharing metadata.

    def test_language_filter_preserves_nested_markup(self):
        parser = build_site.LangFilter('es')
        parser.feed('<div><div class="es">A<div>B</div><img src="x"></div><p class="en">C</p></div>')
        self.assertEqual(''.join(parser.out), '<div><p class="en">C</p></div>')

    def test_year_options_follow_publication_data(self):
        from scripts import content
        read = content.read_data
        def changed(name):
            data = read(name)
            if name == 'publications':
                data = [dict(data[0], year=2030)] + data
            return data
        with patch.object(content, 'read_data', side_effect=changed):
            self.assertIn('<option value="2030">2030</option>', content.render_page('produccion.html'))


if __name__ == '__main__':
    unittest.main()
