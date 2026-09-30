#include "native_input.h"
#include <SDL3/SDL.h>
#include <cassert>
#include <cstdio>
#include <cmath>

static int cx=192,cy=120,writes=0;static bool gameplay=true;
int dune_cursor_get(int*x,int*y){*x=cx;*y=cy;return gameplay;}
void dune_cursor_set(int x,int y){cx=x;cy=y;++writes;}
static void pump(){SDL_PumpEvents();SDL_Event e;while(SDL_PollEvent(&e))dune_input_event(&e);}
static uint16_t capture(){uint16_t b=0;assert(dune_input_capture(&b));return b;}
static void focus(){SDL_Event e{};e.type=SDL_EVENT_WINDOW_FOCUS_GAINED;dune_input_event(&e);}
int main(){
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    assert(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMEPAD));
    auto w=SDL_CreateWindow("Dune input regression",1200,800,SDL_WINDOW_HIDDEN);assert(w);
    auto r=SDL_CreateRenderer(w,nullptr);assert(r);
    assert(SDL_SetRenderLogicalPresentation(r,640,480,SDL_LOGICAL_PRESENTATION_LETTERBOX));
    dune_input_initialize(w);dune_input_viewport(w,r,0,0,640,480,384,240);pump();focus();
    float wx=0,wy=0;assert(SDL_RenderCoordinatesToWindow(r,100.f/384*640,80.f/240*480,&wx,&wy));
    SDL_Event e{};e.type=SDL_EVENT_MOUSE_MOTION;e.motion.x=wx;e.motion.y=wy;e.motion.xrel=1;
    dune_input_event(&e);capture();assert(std::abs(cx-100)<=1&&std::abs(cy-80)<=1);
    int n=writes;capture();capture();assert(writes==n); // no stationary-mouse warp
    e={};e.type=SDL_EVENT_KEY_DOWN;e.key.scancode=SDL_SCANCODE_RETURN;
    assert(dune_input_event(&e)==1);assert((capture()&0x4000)==0);
    SDL_Delay(110);assert((capture()&0x4000)!=0);
    e={};e.type=SDL_EVENT_KEY_DOWN;e.key.scancode=SDL_SCANCODE_RETURN;e.key.mod=SDL_KMOD_ALT;
    assert(dune_input_event(&e)==0);assert((capture()&0x4000)!=0); // fullscreen cannot click a game command
    // Config deliberately remaps Square to X, leaving defaults for other actions.
    e={};e.type=SDL_EVENT_KEY_DOWN;e.key.scancode=SDL_SCANCODE_X;
    assert(dune_input_event(&e)==1);assert((capture()&0x8000)==0);
    SDL_Delay(110);
    e={};e.type=SDL_EVENT_MOUSE_BUTTON_DOWN;e.button.button=SDL_BUTTON_RIGHT;e.button.x=wx;e.button.y=wy;
    dune_input_event(&e);assert((capture()&0x2000)==0);SDL_Delay(110);
    SDL_VirtualJoystickDesc desc{};SDL_INIT_INTERFACE(&desc);
    desc.type=SDL_JOYSTICK_TYPE_GAMEPAD;desc.name="Dune regression virtual gamepad";
    desc.naxes=SDL_GAMEPAD_AXIS_COUNT;desc.nbuttons=SDL_GAMEPAD_BUTTON_COUNT;
    desc.button_mask=(1u<<SDL_GAMEPAD_BUTTON_COUNT)-1;desc.axis_mask=(1u<<SDL_GAMEPAD_AXIS_COUNT)-1;
    auto id=SDL_AttachVirtualJoystick(&desc);assert(id);auto j=SDL_OpenJoystick(id);assert(j);
    pump();focus();assert(SDL_IsGamepad(id));
    assert(SDL_SetJoystickVirtualButton(j,SDL_GAMEPAD_BUTTON_SOUTH,true));pump();
    assert((capture()&0x4000)==0);
    assert(SDL_SetJoystickVirtualButton(j,SDL_GAMEPAD_BUTTON_SOUTH,false));pump();SDL_Delay(110);
    assert(SDL_SetJoystickVirtualAxis(j,SDL_GAMEPAD_AXIS_LEFT_TRIGGER,32767));pump();assert((capture()&0x0100)==0);
    assert(SDL_SetJoystickVirtualAxis(j,SDL_GAMEPAD_AXIS_LEFT_TRIGGER,-32768));pump();
    assert(SDL_SetJoystickVirtualAxis(j,SDL_GAMEPAD_AXIS_LEFTX,25000));pump();
    int old=cx;SDL_Delay(25);capture();assert(cx>old); // stick takes ownership
    old=cx;SDL_Delay(25);capture();assert(cx>old); // mouse does not pull back
    gameplay=false;assert((capture()&0x20)==0); // stick also navigates frontend
    assert(SDL_SetJoystickVirtualAxis(j,SDL_GAMEPAD_AXIS_LEFTX,0));pump();
    assert(SDL_SetJoystickVirtualButton(j,SDL_GAMEPAD_BUTTON_DPAD_UP,true));pump();assert((capture()&0x10)==0);
    SDL_CloseJoystick(j);assert(SDL_DetachVirtualJoystick(id));pump();SDL_Delay(110);assert(capture()==0xffff);
    e={};e.type=SDL_EVENT_WINDOW_FOCUS_LOST;dune_input_event(&e);assert(capture()==0xffff);
    SDL_DestroyRenderer(r);SDL_DestroyWindow(w);SDL_Quit();
    std::puts("PASS: direct mouse, SDL letterbox, short keys, config, buttons, stick ownership, frontend, trigger, hot unplug, focus");
}
