#include "input_core.hpp"
#include <cassert>
#include <cmath>
using namespace dune;
int main(){
    auto eq=[](float a,float b){return std::abs(a-b)<.01f;};
    for(float scale:{1.f,2.f,3.f,1.75f}){
        Viewport v{30,60,384*scale,240*scale,384,240};
        auto p=map_absolute({30+100*scale,60+80*scale},v);
        assert(eq(p.x,100)&&eq(p.y,80));
        p=map_absolute({0,0},v);assert(p.x==0&&p.y==0);
        p=map_absolute({5000,5000},v);assert(p.x==383&&p.y==239);
    }
    assert(deadzone_axis(.1f,.18f)==0);assert(eq(deadzone_axis(-1,.18f),-1));
    auto gain=absolute_gain({100,80},384,240,1);assert(gain.x==100&&gain.y==80);
    gain=absolute_gain({0,240},384,240,4);assert(gain.x==0&&gain.y==239);
    CursorInput c;Point p;c.mouse({100,80});assert(c.consume_absolute(p));
    assert(!c.consume_absolute(p)); // stationary mouse never warps a controller cursor back
    c.mouse({120,90});c.relative();assert(!c.consume_absolute(p));
    c.mouse({150,110});assert(c.consume_absolute(p)&&p.x==150);
    Actions a{};assert(original_buttons(a)==0xffff);a[unsigned(GameAction::Primary)]=true;
    assert(original_buttons(a)==0xbfff);a[unsigned(GameAction::Back)]=true;assert(original_buttons(a)==0xafff);
}
