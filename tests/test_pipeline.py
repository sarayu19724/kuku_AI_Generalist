
import unittest
from engine import parse_episode, build_candidates, run_pack

class PipelineTests(unittest.TestCase):
    def test_timestamp_parser(self):
        raw="""**ACTION:**\nStart: (00:01.00) | End: (00:04.00)\nShe gasps.\n\n**CHARACTER:**\nStart: (00:04.00) | End: (00:25.00)\n\"Who are you?\"\n"""
        ev=parse_episode("episode-001.txt",raw)
        self.assertEqual(len(ev),2)
        self.assertAlmostEqual(ev[1]["end"],25.0)

    def test_duration_constraints(self):
        ev=[{"start":0,"end":25,"label":"ACTION","text":"A shocking attack."},
            {"start":25,"end":45,"label":"CHARACTER","text":"Who did this?"},
            {"start":45,"end":55,"label":"ACTION","text":"The door opens."}]
        cs=build_candidates(ev,1)
        self.assertTrue(all(20<=c["duration"]<=60 for c in cs))

    def test_pack_results(self):
        ev=[{"start":0,"end":25,"label":"ACTION","text":"A shocking attack."},
            {"start":25,"end":45,"label":"CHARACTER","text":"Who did this?"},
            {"start":45,"end":55,"label":"ACTION","text":"The door opens."}]
        cs,stats=run_pack({1:("episode-001.txt","")})
        # Empty screenplay is valid input but yields no candidates.
        self.assertEqual(cs,[])
        self.assertEqual(stats[0]["events_parsed"],0)

if __name__=="__main__": unittest.main()
