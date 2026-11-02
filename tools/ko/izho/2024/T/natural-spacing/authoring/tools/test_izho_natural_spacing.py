"""Regressions for actual trace layouts seen in published IZhO translations."""
import unittest
from izho_natural_spacing import plan_page,boundary_gap,inject_atomic_tokens,records,token

def trace(text,x,y=50,font='NotoSerifCJKkr-Regular',size=12):
    chars=[]
    for c in text:
        w=(3 if c==' 'else 11.592 if ord(c)>=0xac00 else 6)
        chars.append((ord(c),ord(c),(x,y),(x,y-9,x+w,y+3)));x+=w
    return dict(font=font,size=size,chars=chars,dir=(1,0),type=0)

class Page:
    def __init__(self,traces):self.traces=traces
    def get_texttrace(self):return self.traces

class SpacingRegression(unittest.TestCase):
    def test_english_possessive_attaches_only_the_possessive_suffix(self):
        left=dict(text='C_v',kind='native',size=12,x0=20,x1=40)
        for text,gap in [("'s derivative",0),('’s',0),("'some quoted text'",3)]:
            right=dict(text=text,kind='korean',size=12,x0=100,x1=200)
            self.assertEqual(boundary_gap(left,right),gap)

    def test_unclaimed_atomic_pass_preserves_authored_spaces_and_metadata(self):
        rows=records(Page([trace('rdPhysics',100,font='TimesNewRomanPSMT')]))
        item=dict(token(rows,'korean'),text='rd Physics',placement=7,reviewed='original authoring text')
        line=dict(baseline=50,tokens=[item])
        output=inject_atomic_tokens([line],[])[0]['tokens'][0]
        self.assertEqual(output,item)
        left=dict(text='23',kind='native',size=12,x0=20,x1=32)
        self.assertEqual(boundary_gap(left,output),0)
        output['text']='인 강체구'
        self.assertEqual(boundary_gap(dict(left,text='m'),output),0)

    def test_all_native_math_gaps_including_punctuation_remain_original(self):
        left=dict(text='x',kind='native',size=12,x0=20,x1=26)
        for text,x in[('y',50),(',',29),(')',28)]:
            right=dict(text=text,kind='native',size=12,x0=x,x1=x+6)
            self.assertEqual(boundary_gap(left,right),x-26)

    def test_ordinal_prefix_does_not_attach_a_word_ending_with_je(self):
        for before,gap in [('제',0),('이제',3),('문제',3)]:
            page=Page([trace(before,20),trace('40',100,font='TimesNewRomanPSMT'),trace('회',150)])
            out=plan_page(page,allowed_line_rects=[[19,35,230,65]])
            self.assertEqual(out['lines'][0]['gaps'][0]['new_gap'],gap)
            self.assertEqual(out['lines'][0]['gaps'][-1]['new_gap'],0)

    def test_tiny_source_baseline_rounding_is_one_line_without_changing_y(self):
        page=Page([trace('질량',20,50),trace('은',100,50.011)])
        out=plan_page(page,allowed_line_rects=[[19,35,180,65]])
        self.assertEqual(len(out['lines']),1)
        self.assertEqual(out['shifts'][0]['glyphs'][0]['origin'][1],50.011)

    def test_particle_attachment_does_not_join_a_noun_starting_the_same_letter(self):
        for following,gap in [('인 강체구',0),('이다.',0),('이산화탄소',3),('인덕턴스',3)]:
            page=Page([trace('질량',20),trace('m',100,font='TimesNewRomanPSMT'),trace(following,150)])
            out=plan_page(page,allowed_line_rects=[[19,35,300,65]])
            self.assertEqual(out['lines'][0]['gaps'][-1]['new_gap'],gap,following)

    def test_multi_unicode_source_cid_keeps_nonpainting_continuation_in_shift(self):
        native=trace('f',100,font='CambriaMath')
        native['chars'].append((ord('i'),-1,(100,50),(100,41,100,53)))
        page=Page([trace('변수',20),native,trace('를',150)])
        out=plan_page(page,allowed_line_rects=[[19,35,220,65]])
        math=next(s for s in out['shifts']if s['glyphs'][0]['font']=='CambriaMath')
        self.assertEqual([r['c']for r in math['glyphs']],['f','i'])

    def test_two_columns_at_equal_baseline_never_merge(self):
        page=Page([trace('질량',20),trace('m',150,font='TimesNewRomanPSMT'),
                   trace('속도',260),trace('v',410,font='TimesNewRomanPSMT')])
        out=plan_page(page,allowed_line_rects=[[19,35,200,65],[259,35,450,65]],word_space_pt=3)
        self.assertEqual(len(out['lines']),2)
        self.assertLess(out['lines'][0]['new_right'],200)
        self.assertGreater(out['lines'][1]['tokens'][0]['new_x0'],250)

    def test_native_ascii_and_korean_suffix_are_one_authored_placement(self):
        page=Page([trace('2021',20,font='TimesNewRomanPSMT'),trace('년',44)])
        out=plan_page(page,allowed_line_rects=[[19,35,100,65]],
                      prose_placements=[dict(point=[20,50],width=35.592,text='2021년')])
        self.assertEqual(len(out['lines'][0]['tokens']),1)
        self.assertAlmostEqual(out['lines'][0]['new_right'],55.592)
        self.assertFalse(out['shifts'])

    def test_one_native_trace_spanning_erased_prose_is_split(self):
        native=trace('µm',20,font='CIDFont+F3')
        native['chars']+=trace('6.50',110,font='CIDFont+F3')['chars']
        native['chars']+=trace('7.00',240,font='CIDFont+F3')['chars']
        page=Page([native,trace('및',60),trace('와',150)])
        out=plan_page(page,allowed_line_rects=[[19,35,300,65]])
        self.assertEqual([t['text']for t in out['lines'][0]['tokens']],['µm','및','6.50','와','7.00'])
        self.assertLess(out['lines'][0]['new_right'],120)

    def test_display_equation_without_prose_on_its_baseline_does_not_move(self):
        page=Page([trace('질량',20),trace('m',150,font='TimesNewRomanPSMT'),trace('E=mc2',180,100,font='CambriaMath')])
        out=plan_page(page,allowed_line_rects=[[19,35,300,120]])
        self.assertTrue(all(r['origin'][1]==50 for s in out['shifts']for r in s['glyphs']))

    def test_math_subscript_retains_relative_geometry(self):
        page=Page([trace('힘',20),trace('T',150,font='CambriaMath'),trace('0',156,52.4,font='CambriaMath',size=8.52),trace('를',164)])
        out=plan_page(page,allowed_line_rects=[[19,35,200,65]])
        math=out['lines'][0]['tokens'][1]
        self.assertEqual(math['text'],'T0')
        self.assertAlmostEqual(math['glyphs'][1]['origin'][1]-math['glyphs'][0]['origin'][1],2.4)
        self.assertEqual(out['lines'][0]['gaps'][-1]['new_gap'],0)

if __name__=='__main__':unittest.main()
