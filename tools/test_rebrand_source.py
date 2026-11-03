import unittest
from prepare_play_sources import rust_strings

class SourceBrandingTest(unittest.TestCase):
    def test_rust_identifiers_comments_and_quote_char_remain_unchanged(self):
        source='''// PhotoCraft "unfinished comment quote
impl PhotoCraftApp {
  fn label(&self) -> &'static str {
    let quote = '"';
    /* nested /* "PhotoCraft */ comment */
    "PhotoCraft document"
  }
}
'''
        result=rust_strings(source,lambda text:text.replace('PhotoCraft','Photos'))
        self.assertIn('impl PhotoCraftApp',result)
        self.assertIn('// PhotoCraft "unfinished comment quote',result)
        self.assertIn('/* nested /* "PhotoCraft */ comment */',result)
        self.assertIn('"Photos document"',result)
        self.assertIn("let quote = '\"';",result)
    def test_raw_and_escaped_strings_are_rewritten_without_touching_code(self):
        source='let s = r##"PhotoCraft says "hi""##; let t = "PhotoCraft \\"quoted\\""; struct PhotoCraftApp;'
        result=rust_strings(source,lambda text:text.replace('PhotoCraft','Photos'))
        self.assertIn('r##"Photos says "hi""##',result)
        self.assertIn('struct PhotoCraftApp',result)
    def test_unterminated_raw_string_is_rejected(self):
        with self.assertRaises(ValueError):rust_strings('r#"unfinished',lambda text:text)

if __name__=='__main__':unittest.main()
