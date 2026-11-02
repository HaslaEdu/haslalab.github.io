import unittest
from izho_natural_spacing import authored_fragment,inject_atomic_tokens

class PartialAuthoredWordSpaceTests(unittest.TestCase):
    def test_korean_fragment_keeps_real_word_spaces(self):
        self.assertEqual(authored_fragment(' 문제를 풀기 위해 아래 그림을 그리자.','문제를풀기위해아래그림을그리자'),' 문제를 풀기 위해 아래 그림을 그리자')
    def test_english_ordinal_fragment(self):
        self.assertEqual(authored_fragment('23rd Physics Competition','rdPhysicsCompetition'),'rd Physics Competition')
    def test_ambiguous_fragment_is_not_guessed(self):
        self.assertIsNone(authored_fragment('일 일 일','일'))
    def test_unmatched_fragment_is_not_guessed(self):
        self.assertIsNone(authored_fragment('α + β','unmatched'))
    def test_partial_atom_claim_preserves_unclaimed_prose_words(self):
        text='문제를 풀기 위해 아래 그림을 그리자.';chars=''.join(text.split())
        rows=[dict(c=c,font='Fake',size=12.,origin=[i*6.,12.],bbox=[i*6.,0,i*6.+5,14],gid=i,trace=i,index=0)for i,c in enumerate(chars)]
        item=dict(kind='korean',text=text,glyphs=rows,x0=0,x1=len(rows)*6.,y=12.,size=12.,fonts=['Fake'],placement=0)
        atom=dict(kind='native',text='.',glyphs=[rows[-1]],x0=(len(rows)-1)*6.,x1=len(rows)*6.,y=12.,size=12.,fonts=['Fake'])
        lines=inject_atomic_tokens([dict(baseline=12.,tokens=[item])],[atom])
        self.assertEqual(lines[0]['tokens'][0]['text'],'문제를 풀기 위해 아래 그림을 그리자')

class ComposerFragmentFallbackTests(unittest.TestCase):
    def test_fragment_without_source_period_retains_five_wordspaces(self):
        from pdf_korean_natural_composer import _units
        class Metric:
            def text_length(self,text,fontsize):return len(text)*fontsize
        text='문제를 풀기 위해 아래 그림을 그리자.';chars=''.join(text.split())[:-1]
        rows=[dict(c=c,font='NotoSerifCJKkr-Regular',size=12.,origin=[i*12.,12.],bbox=[i*12.,0,i*12.+11.5,14],gid=i,trace=i,index=0)for i,c in enumerate(chars)]
        item=dict(kind='korean',text=chars,glyphs=rows,x0=0,x1=len(rows)*12.,y=12.,size=12.,fonts=['NotoSerifCJKkr-Regular'],placement=0)
        units=_units(item,[dict(text=text,point=[0,12],width=1000)],Metric())
        self.assertEqual(sum(u['kind']=='space'for u in units),5)
        self.assertEqual([u['text']for u in units if u['kind']=='batang'],['문제를','풀기','위해','아래','그림을','그리자'])

if __name__=='__main__':unittest.main()
