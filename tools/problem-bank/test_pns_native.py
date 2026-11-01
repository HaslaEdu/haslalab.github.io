"""Synthetic source-coordinate and number-identity checks, without OCR calls."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('pns_native', Path(__file__).with_name('extract-pns-native.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativeProfileTests(unittest.TestCase):
    def test_local_ocr_points_and_source_identity(self):
        record = {'engine': 'tesseract-local', 'source_sha256': '0' * 64, 'page': 2,
                  'page_size_pt': [100, 200], 'render_size_px': [1000, 2000],
                  'tsv': 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
                         '5\t2\t1\t1\t1\t1\t450\t600\t100\t100\t95\t1036\n'}
        lines = MODULE.local_ocr_lines(record, '0' * 64, 2, [100, 200])
        self.assertEqual(lines[0]['bbox'], [45, 60, 55, 70])
        self.assertEqual(lines[0]['text'], '1036')
        without_header = copy.deepcopy(record)
        without_header['tsv'] = without_header['tsv'].split('\n', 1)[1]
        self.assertEqual(MODULE.local_ocr_lines(without_header, '0' * 64, 2, [100, 200]), lines)
        with self.assertRaisesRegex(ValueError, 'source/page mismatch'):
            MODULE.local_ocr_lines(record, '1' * 64, 2, [100, 200])
        malformed = copy.deepcopy(record)
        malformed['render_size_px'] = [50, 2000]
        with self.assertRaisesRegex(ValueError, 'outside'):
            MODULE.local_ocr_lines(malformed, '0' * 64, 2, [100, 200])

    def test_number_labels_belong_to_their_own_part_pages(self):
        profile = {'layout': {}, 'parts': [
            {'part': 2, 'first_page': 1, 'last_page': 1, 'first_number': 2003, 'last_number': 2003, 'expected_count': 1},
            {'part': 8, 'first_page': 2, 'last_page': 2, 'first_number': 8001, 'last_number': 8001, 'expected_count': 1}]}
        pages = [{'page': 1, 'width': 100, 'height': 200, 'lines': [
                    {'page': 1, 'text': '2003', 'bbox': [45, 60, 55, 70]}]},
                 {'page': 2, 'width': 100, 'height': 200, 'lines': [
                    {'page': 2, 'text': '8001', 'bbox': [45, 60, 55, 70]},
                    {'page': 2, 'text': '2003', 'bbox': [45, 100, 55, 110]}]}]
        result = MODULE.number_headers(pages, profile, {})
        self.assertEqual([row['number'] for row in result], ['2003', '8001'])

    def test_nonstandard_ocr_label_requires_a_reviewed_private_correction(self):
        profile = {'layout': {}, 'parts': [
            {'part': 8, 'first_page': 1, 'last_page': 1, 'first_number': 8007, 'last_number': 8007, 'expected_count': 1}]}
        label = {'page': 1, 'text': "800'7", 'bbox': [45, 60, 55, 70]}
        pages = [{'page': 1, 'width': 100, 'height': 200, 'lines': [label]}]
        correction = {'page': 1, 'raw_label': "800'7", 'number': '8007',
                      'bbox': label['bbox'], 'source_image_checked': True}
        self.assertEqual(MODULE.number_headers(pages, profile, {'number_labels': [correction]})[0]['number'], '8007')
        correction['source_image_checked'] = False
        with self.assertRaisesRegex(ValueError, 'Unreviewed number discrepancy'):
            MODULE.number_headers(pages, profile, {'number_labels': [correction]})

    def test_printed_typo_keeps_its_observed_number_separate_from_sequence(self):
        profile = {'layout': {}, 'parts': [
            {'part': 5, 'first_page': 1, 'last_page': 1, 'first_number': 5026, 'last_number': 5026, 'expected_count': 1}]}
        pages = [{'page': 1, 'width': 100, 'height': 200,
                  'lines': [{'page': 1, 'text': '5626', 'bbox': [45, 60, 55, 70]}]}]
        correction = {'page': 1, 'raw_label': '5626', 'number': '5026', 'printed_number': '5626',
                      'printed_label_typo': True, 'bbox': [45, 60, 55, 70], 'source_image_checked': True}
        result = MODULE.number_headers(pages, profile, {'number_labels': [correction]})[0]
        self.assertEqual((result['number'], result['printed_number']), ('5026', '5626'))
        correction['printed_label_typo'] = False
        with self.assertRaisesRegex(ValueError, 'explicit source-typo record'):
            MODULE.number_headers(pages, profile, {'number_labels': [correction]})

    def test_compact_page_solution_header_uses_its_profile_top(self):
        pages = [{'lines': [{'page': 1, 'text': 'Solution:', 'bbox': [20, 52, 60, 62]}]}]
        self.assertEqual(MODULE.solution_headers(pages, {}), [])
        self.assertEqual(len(MODULE.solution_headers(pages, {}, min_top=48)), 1)

    def test_duplicate_scan_label_exclusion_requires_matching_reviewed_region(self):
        profile = {'layout': {}, 'parts': [
            {'part': 4, 'first_page': 1, 'last_page': 2, 'first_number': 4060,
             'last_number': 4060, 'expected_count': 1}]}
        pages = [{'page': n, 'width': 100, 'height': 200, 'lines': [
            {'page': n, 'text': '4060', 'bbox': [45, 60, 55, 70]}]} for n in [1, 2]]
        exclusion = {'page': 1, 'raw_label': '4060', 'bbox': [45, 60, 55, 70],
                     'source_image_checked': True, 'review_note': 'Duplicate scanned printed page.'}
        overrides = {'number_label_exclusions': [exclusion]}
        self.assertEqual(MODULE.number_headers(pages, profile, overrides)[0]['page'], 2)
        exclusion['source_image_checked'] = False
        with self.assertRaisesRegex(ValueError, 'reviewed source region'):
            MODULE.number_headers(pages, profile, overrides)
        exclusion['source_image_checked'] = True
        exclusion['page'] = 3
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            MODULE.number_headers(pages, profile, overrides)


if __name__ == '__main__':
    unittest.main()
