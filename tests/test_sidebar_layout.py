"""Resizable sidebars are local UI preferences, never mathematical edits."""
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "backend/static/sidebar-layout.js"


def run_js(body):
    setup = r"""
const api = require(process.argv[1]);
class Node {
  constructor(side) { this.dataset = side ? {sidebarResizer:side} : {}; this.events={}; this.attrs={};
    this.classList={add:()=>{},remove:()=>{}}; this.style={setProperty:(k,v)=>this.attrs[k]=v}; }
  addEventListener(name, callback) { this.events[name]=callback; }
  setAttribute(name, value) { this.attrs[name]=value; }
  focus() {} setPointerCapture(id) {this.capture=id;} hasPointerCapture(id) {return this.capture===id;}
  releasePointerCapture() {this.capture=null;}
  fire(name, props={}) { this.events[name]?.({button:0,pointerId:1,clientX:0,preventDefault(){},stopPropagation(){},...props}); }
}
function mock(width=1411, saved=null, blockedStorage=false) {
  const handles=[new Node('left'),new Node('right')], layout=new Node(), events={}, frames=[];
  let value=saved, calls=0;
  const win={innerWidth:width,addEventListener:(k,v)=>events[k]=v,
    requestAnimationFrame:f=>{frames.push(f);return frames.length;},
    localStorage:{getItem(){if(blockedStorage)throw Error('denied');return value;},setItem(k,v){if(blockedStorage)throw Error('denied');value=v;}}};
  layout.ownerDocument={defaultView:win,body:new Node()};
  layout.getBoundingClientRect=()=>({width:win.innerWidth}); layout.querySelectorAll=()=>handles;
  api.mount(layout,()=>calls++);
  return {layout,handles,win,events,value:()=>value,flush:()=>{while(frames.length)frames.shift()();return calls;}};
}
"""
    result = subprocess.run(["node", "-e", setup + "\n" + body, str(MODULE)],
                            capture_output=True, encoding="utf-8", check=True, timeout=20)
    return json.loads(result.stdout)


@pytest.mark.parametrize("width,visible", [(1411, True), (1041, True), (1040, False), (800, False)])
def test_restored_widths_preserve_chart_and_minimum_panel_sizes(width, visible):
    result = run_js(f"process.stdout.write(JSON.stringify(api.fitWidths({width},{{left:9999,right:9999}},{str(visible).lower()})));")
    assert 180 <= result["left"] <= 520
    assert (220 <= result["right"] <= 560) if visible else result["right"] == 0
    assert width - result["left"] - result["right"] >= 320 - 1e-8


def test_pointer_drag_both_sides_save_and_keyboard_reset():
    result = run_js("""
const m=mock(), [left,right]=m.handles;
left.fire('pointerdown',{clientX:300}); left.fire('pointermove',{clientX:350}); left.fire('pointerup');
right.fire('pointerdown',{clientX:1031}); right.fire('pointermove',{clientX:991}); right.fire('pointerup');
const dragged=JSON.parse(m.value());
left.fire('keydown',{key:'ArrowLeft'}); right.fire('keydown',{key:'ArrowRight',shiftKey:true});
const keyed=JSON.parse(m.value()); left.fire('dblclick'); right.fire('dblclick');
process.stdout.write(JSON.stringify({dragged,keyed,reset:JSON.parse(m.value()),attrs:m.handles.map(x=>x.attrs),redraws:m.flush()}));
""")
    assert result["dragged"] == {"left": 350, "right": 420}
    assert result["keyed"] == {"left": 340, "right": 380}
    assert result["reset"] == {}
    assert [p["aria-valuenow"] for p in result["attrs"]] == ["300", "380"]
    assert result["redraws"] == 1  # coalesced instead of repainting for every pointer event


def test_pointer_cancel_escape_and_foreign_pointer_do_not_persist():
    result = run_js("""
const m=mock(), left=m.handles[0];
left.fire('pointerdown',{clientX:300}); left.fire('pointermove',{clientX:400,pointerId:2});
const foreign=left.attrs['aria-valuenow'];
left.fire('pointermove',{clientX:450}); left.fire('pointercancel');
const cancelled=left.attrs['aria-valuenow'];
left.fire('pointerdown',{clientX:300}); left.fire('pointermove',{clientX:450}); left.fire('keydown',{key:'Escape'});
process.stdout.write(JSON.stringify({foreign,cancelled,escaped:left.attrs['aria-valuenow'],saved:m.value()}));
""")
    assert result == {"foreign": "300", "cancelled": "300", "escaped": "300", "saved": None}


def test_browser_resize_temporarily_clamps_but_does_not_lose_saved_widths():
    result = run_js("""
const m=mock(1600,JSON.stringify({left:500,right:500}));
m.win.innerWidth=1041;m.events.resize();const narrow=m.handles.map(x=>Number(x.attrs['aria-valuenow']));
m.win.innerWidth=1600;m.events.resize();const restored=m.handles.map(x=>Number(x.attrs['aria-valuenow']));
process.stdout.write(JSON.stringify({narrow,restored,saved:JSON.parse(m.value())}));
""")
    assert sum(result["narrow"]) <= 722
    assert result["restored"] == [500, 500]
    assert result["saved"] == {"left": 500, "right": 500}


@pytest.mark.parametrize("saved,blocked", [("not json", False), ('{"left":"bad","right":null}', False), (None, True)])
def test_invalid_or_disabled_storage_is_nonfatal(saved, blocked):
    result = run_js(f"""
const m=mock(1411,{json.dumps(saved)},{str(blocked).lower()});
m.handles[0].fire('keydown',{{key:'ArrowRight'}});
process.stdout.write(JSON.stringify(m.handles[0].attrs['aria-valuenow']));
""")
    assert result == "310"


def test_hidden_mobile_handles_ignore_pointer_drag():
    result = run_js("""
const m=mock(700);m.handles[0].fire('pointerdown');m.handles[0].fire('pointermove',{clientX:100});m.handles[0].fire('pointerup');
process.stdout.write(JSON.stringify(m.value()));
""")
    assert result is None


def test_accessibility_breakpoints_and_static_mirror():
    template = (ROOT / "backend/templates/index.html").read_text(encoding="utf-8")
    assert template.count('role="separator"') == 2
    assert template.count('aria-orientation="vertical"') == 2
    assert 'aria-controls="left-sidebar"' in template and 'aria-controls="right-sidebar"' in template
    assert "sidebar-layout.js" in template
    css = (ROOT / "backend/static/style.css").read_text(encoding="utf-8")
    assert '.sidebar-resizer:hover::after' in css
    assert 'touch-action: none' in css
    assert '.sidebar-resizer { display: none; }' in css
    assert MODULE.read_bytes() == (ROOT / "public/static/sidebar-layout.js").read_bytes()
