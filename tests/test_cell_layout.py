import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "backend" / "static" / "cell-layout.js"


def run_layout(records, cell_size):
    script = """
const layout = require(process.argv[1]);
const records = JSON.parse(process.argv[2]);
const result = layout.packInstances(records, Number(process.argv[3]));
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(LAYOUT), json.dumps(records), str(cell_size)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


class CellLayoutTest(unittest.TestCase):
    def test_two_power_style_stack_uses_responsive_y_offset_without_overlap(self):
        records = [
            {"key": "base", "cellKey": "8:0", "label": "D", "shape": "square", "size": 5.5},
            {"key": "double", "cellKey": "8:0", "label": "2D", "shape": "circle", "size": 5.5},
        ]
        packed = run_layout(records, 28)
        self.assertEqual([item["key"] for item in packed], ["base", "double"])
        separation = abs(packed[1]["dy"] - packed[0]["dy"])
        self.assertGreaterEqual(separation, 0.16 * 28)
        self.assertGreaterEqual(separation, packed[0]["size"] + packed[1]["size"])
        self.assertTrue(all(item["baseYOffset"] == 0.16 for item in packed))

    def test_mixed_fate_glyphs_pack_deterministically_inside_the_cell(self):
        records = [
            {"key": f"class-{index}", "cellKey": "11:15", "label": str(index), "shape": "square" if index % 2 else "circle", "size": 5.5}
            for index in range(6)
        ]
        forward = run_layout(records, 28)
        reverse = run_layout(list(reversed(records)), 28)
        coordinates = lambda result: {item["key"]: (item["dx"], item["dy"], item["size"]) for item in result}
        self.assertEqual(coordinates(forward), coordinates(reverse))
        self.assertEqual(len({(item["dx"], item["dy"]) for item in forward}), 6)
        for item in forward:
            self.assertLessEqual(abs(item["dx"]) + item["size"], 14)
            self.assertLessEqual(abs(item["dy"]) + item["size"], 14)

    def test_small_zoom_shrinks_glyphs_and_keeps_periodic_instances_clickable(self):
        records = [
            {"key": "base", "cellKey": "0:0", "label": "x", "shape": "circle", "size": 5.5},
            {"key": "periodic", "cellKey": "0:0", "label": "x", "shape": "circle", "size": 4.2, "periodic": True},
            {"key": "accepted", "cellKey": "0:0", "label": "a", "shape": "square", "size": 5.5},
        ]
        normal = run_layout(records, 28)
        zoomed_out = run_layout(records, 5)
        self.assertLess(max(item["size"] for item in zoomed_out), max(item["size"] for item in normal))
        self.assertEqual({item["key"] for item in zoomed_out}, {"base", "periodic", "accepted"})
        self.assertTrue(all(item["hitRadius"] >= item["size"] for item in zoomed_out))
        self.assertEqual(len({(item["dx"], item["dy"]) for item in zoomed_out}), 3)


if __name__ == "__main__":
    unittest.main()
