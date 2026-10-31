"""Actual source Latin survives while only missing replacement prose is filled."""
from io import BytesIO
import hashlib,json,unittest
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import cpho_2013_original_fonts as fonts

class OriginalLatinTests(unittest.TestCase):
    def test_source_live_glyphs_are_identical_and_missing_latin_is_visible(self):
        source_sha=fonts.sha(fonts.source.SOURCE)
        for face in ['SimSun','SimHei']:
            target=fonts.english_face(face);report=json.loads(target.with_suffix('.font-provenance.json').read_text('utf8'))
            with fitz.open(fonts.source.SOURCE)as doc:
                record=next(r for r in doc[0].get_fonts()if r[3].split('+')[-1]==face)
                original=TTFont(BytesIO(doc.extract_font(record[0])[3]))
            replacement=TTFont(target);old_set=original.getGlyphSet();new_set=replacement.getGlyphSet()
            for row in report['actual_source_glyphs_kept']:
                old=RecordingPen();new=RecordingPen();old_set[row['glyph']].draw(old);new_set[row['glyph']].draw(new)
                self.assertEqual(old.value,new.value)
                self.assertEqual(original.getGlyphID(row['glyph']),replacement.getGlyphID(row['glyph']))
                self.assertEqual(original['hmtx'][row['glyph']],replacement['hmtx'][row['glyph']])
            for row in report['missing_actual_glyphs_filled']:
                name=replacement.getBestCmap()[ord(row['char'])]
                pen=RecordingPen();new_set[name].draw(pen)
                if not row['char'].isspace():self.assertTrue(pen.value)
                self.assertGreater(replacement['hmtx'][name][0],0)
            self.assertEqual(original['head'].unitsPerEm,replacement['head'].unitsPerEm)
            original.close();replacement.close()
        self.assertEqual(source_sha,fonts.sha(fonts.source.SOURCE))

if __name__=='__main__':unittest.main()
