#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace dune {
enum class GameAction { Primary, Secondary, Square, Triangle, Menu, Back,
    CursorUp, CursorDown, CursorLeft, CursorRight, L1, R1, L2, R2,
    Start, Select, L3, R3, Count };
constexpr unsigned ActionCount=static_cast<unsigned>(GameAction::Count);
using Actions=std::array<bool,ActionCount>;
enum class CursorOwner { Mouse, Relative };
struct Point { float x=0,y=0; };
struct Viewport { float x=0,y=0,w=640,h=480; int logical_w=384,logical_h=240; };
inline Point map_absolute(Point point,Viewport view) {
    if(view.w<=0 || view.h<=0 || view.logical_w<1 || view.logical_h<1)return {};
    return {std::clamp((point.x-view.x)*view.logical_w/view.w,0.f,float(view.logical_w-1)),
            std::clamp((point.y-view.y)*view.logical_h/view.h,0.f,float(view.logical_h-1))};
}
inline float deadzone_axis(float value,float deadzone) {
    float d=std::clamp(deadzone,0.f,.95f),a=std::abs(value);
    return a<=d?0.f:std::copysign(std::min((a-d)/(1-d),1.f),value);
}
inline Point absolute_gain(Point p,int w,int h,float gain) {
    float x=(w-1)*.5f,y=(h-1)*.5f;
    return {std::clamp(x+(p.x-x)*gain,0.f,float(w-1)),
            std::clamp(y+(p.y-y)*gain,0.f,float(h-1))};
}
class CursorInput {
public:
    CursorOwner owner=CursorOwner::Relative;
    bool mouse_dirty=false;
    Point pending{};
    void mouse(Point point){pending=point;mouse_dirty=true;owner=CursorOwner::Mouse;}
    void relative(){owner=CursorOwner::Relative;mouse_dirty=false;}
    bool consume_absolute(Point& point){
        if(owner!=CursorOwner::Mouse || !mouse_dirty)return false;
        point=pending;mouse_dirty=false;return true;
    }
    void reset(){mouse_dirty=false;owner=CursorOwner::Relative;}
};
// Temporary adapter at the boundary to the original controller action reader.
// Host input and bindings never deal in CPU registers or SIO hardware.
inline uint16_t original_buttons(const Actions& a) {
    constexpr unsigned bits[]={14,13,15,12,3,12,4,6,7,5,10,11,8,9,3,0,1,2};
    uint16_t word=0xffff;
    for(unsigned i=0;i<ActionCount;i++)if(a[i])word&=uint16_t(~(1u<<bits[i]));
    return word;
}
}
