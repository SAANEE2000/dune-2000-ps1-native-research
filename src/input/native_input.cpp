#include "native_input.h"
#include "input_core.hpp"
#include <SDL3/SDL.h>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <cstdlib>
#include <cstdio>

namespace {
using namespace dune;
const char* names[]={"Primary","Secondary","Square","Triangle","Menu","Back","CursorUp","CursorDown",
    "CursorLeft","CursorRight","L1","R1","L2","R2","Start","Select","L3","R3"};
struct Bind { enum Kind { Key, Mouse, Pad, Trigger } kind; int code; };
std::array<std::vector<Bind>,ActionCount> bindings;
std::map<SDL_JoystickID,SDL_Gamepad*> pads;
SDL_Window *window=nullptr; SDL_Renderer *renderer=nullptr;
Viewport viewport;
CursorInput cursor;
bool initialized=false,native_mode=true,focused=true;
float stick_speed=220.f,stick_deadzone=.18f;
float mouse_gain=1.f;
uint64_t previous_time=0;
float remainder_x=0,remainder_y=0;
std::array<uint64_t,ActionCount> pulse_until{};
int wheel_up=-1,wheel_down=-1;

int action_index(const std::string& name){for(unsigned i=0;i<ActionCount;i++)if(name==names[i])return int(i);return -1;}
std::string trim(std::string s){auto a=s.find_first_not_of(" \t\r\n");if(a==s.npos)return {};return s.substr(a,s.find_last_not_of(" \t\r\n")-a+1);}
void set_binding(unsigned action,const std::string& spec) {
    std::istringstream stream(spec);std::string item;
    bindings[action].clear();
    while(std::getline(stream,item,',')) {
        item=trim(item);auto slash=item.find('/');if(slash==item.npos)continue;
        auto type=item.substr(0,slash),value=item.substr(slash+1);
        if(type=="Key") {auto sc=SDL_GetScancodeFromName(value.c_str());if(sc!=SDL_SCANCODE_UNKNOWN)bindings[action].push_back({Bind::Key,int(sc)});}
        else if(type=="Mouse") {int button=value=="Left"?SDL_BUTTON_LEFT:value=="Right"?SDL_BUTTON_RIGHT:value=="Middle"?SDL_BUTTON_MIDDLE:0;if(button)bindings[action].push_back({Bind::Mouse,button});}
        else if(type=="Pad") {
            // SDL3 renamed the enums; SDL's mapping strings retain a/b/x/y.
            auto b=value=="south"?SDL_GAMEPAD_BUTTON_SOUTH:value=="east"?SDL_GAMEPAD_BUTTON_EAST:
                value=="west"?SDL_GAMEPAD_BUTTON_WEST:value=="north"?SDL_GAMEPAD_BUTTON_NORTH:
                SDL_GetGamepadButtonFromString(value.c_str());
            if(b!=SDL_GAMEPAD_BUTTON_INVALID)bindings[action].push_back({Bind::Pad,int(b)});
            else std::fprintf(stderr,"DUNE_INPUT invalid pad button: %s\n",value.c_str());
        }
        else if(type=="Axis" && (value=="left_trigger"||value=="right_trigger"))bindings[action].push_back({Bind::Trigger,value=="left_trigger"?SDL_GAMEPAD_AXIS_LEFT_TRIGGER:SDL_GAMEPAD_AXIS_RIGHT_TRIGGER});
    }
}
void refresh_pads() {
    for(auto it=pads.begin();it!=pads.end();) {
        if(!SDL_GamepadConnected(it->second)){SDL_CloseGamepad(it->second);it=pads.erase(it);}else ++it;
    }
    int count=0;SDL_JoystickID* ids=SDL_GetGamepads(&count);
    for(int i=0;i<count;i++)if(!pads.count(ids[i]))if(auto p=SDL_OpenGamepad(ids[i]))pads[ids[i]]=p;
    SDL_free(ids);
}
void initialize() {
    if(initialized)return;initialized=true;
    const char *defaults[]={"Key/Return,Key/Space,Mouse/Left,Pad/south","Mouse/Right,Pad/east","Key/Z,Pad/west","Key/C,Pad/north",
        "Key/Tab","Key/Escape","Key/Up,Key/W,Pad/dpup","Key/Down,Key/S,Pad/dpdown","Key/Left,Key/A,Pad/dpleft","Key/Right,Key/D,Pad/dpright",
        "Key/Q,Pad/leftshoulder","Key/E,Pad/rightshoulder","Key/1,Axis/left_trigger","Key/3,Axis/right_trigger","Key/F10,Pad/start","Key/Backspace,Pad/back",
        "Pad/leftstick","Pad/rightstick"};
    for(unsigned i=0;i<ActionCount;i++)set_binding(i,defaults[i]);
    const char* env=std::getenv("DUNE_INPUT_CONFIG");
    const char* path=env&&*env?env:DUNE_INPUT_CONFIG_PATH;
    std::ifstream file(path);std::string line,section;
    while(std::getline(file,line)) {
        line=trim(line.substr(0,line.find_first_of("#;")));if(line.empty())continue;
        if(line.front()=='['&&line.back()==']'){section=line.substr(1,line.size()-2);continue;}
        auto eq=line.find('=');if(eq==line.npos)continue;auto key=trim(line.substr(0,eq)),value=trim(line.substr(eq+1));
        if(section=="bindings") {int a=action_index(key);if(a>=0)set_binding(unsigned(a),value);}
        else if(section=="input") {
            if(key=="mode")native_mode=(value!="PS1Compatible");
            else if(key=="mouse_sensitivity")mouse_gain=std::clamp(float(std::atof(value.c_str())),1.f,4.f);
            else if(key=="controller_cursor_speed")stick_speed=std::clamp(float(std::atof(value.c_str())),1.f,1000.f);
            else if(key=="controller_deadzone")stick_deadzone=std::clamp(float(std::atof(value.c_str())),0.f,.95f);
            else if(key=="wheel_up")wheel_up=action_index(value);
            else if(key=="wheel_down")wheel_down=action_index(value);
        }
    }
    refresh_pads();
    std::fprintf(stderr,"DUNE_INPUT mode=%s config=%s pads=%zu\n",native_mode?"Native":"PS1Compatible",path,pads.size());
}
bool direction_key(SDL_Scancode code) {
    for(unsigned i=unsigned(GameAction::CursorUp);i<=unsigned(GameAction::CursorRight);i++)
        for(auto b:bindings[i])if(b.kind==Bind::Key && b.code==code)return true;
    return false;
}
Point window_to_game(float x,float y) {
    if(renderer) {float rx=x,ry=y;if(SDL_RenderCoordinatesFromWindow(renderer,x,y,&rx,&ry))return map_absolute({rx,ry},viewport);}
    int w=640,h=480;if(window)SDL_GetWindowSize(window,&w,&h);
    float scale=std::min(w/640.f,h/480.f);
    return map_absolute({x,y},{(w-640*scale)/2,(h-480*scale)/2,640*scale,480*scale,384,240});
}
}

void dune_input_initialize(SDL_Window *w){window=w;initialize();}
void dune_input_viewport(SDL_Window *w,SDL_Renderer *r,float x,float y,float width,float height,int lw,int lh) {
    window=w;renderer=r;viewport={x,y,width,height,lw,lh};initialize();
}
int dune_input_event(const SDL_Event *event) {
    initialize();const auto& e=*event;
    if(e.type==SDL_EVENT_GAMEPAD_ADDED || e.type==SDL_EVENT_GAMEPAD_REMOVED)refresh_pads();
    if(!native_mode)return 0;
    if(e.type==SDL_EVENT_WINDOW_FOCUS_LOST){focused=false;cursor.reset();pulse_until.fill(0);}
    if(e.type==SDL_EVENT_WINDOW_FOCUS_GAINED)focused=true;
    if(e.type==SDL_EVENT_MOUSE_MOTION && (e.motion.xrel!=0 || e.motion.yrel!=0))cursor.mouse(absolute_gain(window_to_game(e.motion.x,e.motion.y),384,240,mouse_gain));
    if(e.type==SDL_EVENT_MOUSE_BUTTON_DOWN)cursor.mouse(absolute_gain(window_to_game(e.button.x,e.button.y),384,240,mouse_gain));
    const uint64_t now=SDL_GetTicksNS();
    // Preserve short press edges across the original game's slower pad poll.
    // Direction keys retain their original held/repeat behavior.
    for(unsigned i=0;i<ActionCount;i++) {
        if(i>=unsigned(GameAction::CursorUp)&&i<=unsigned(GameAction::CursorRight))continue;
        for(auto b:bindings[i]) {
            bool host_fullscreen=e.type==SDL_EVENT_KEY_DOWN&&e.key.scancode==SDL_SCANCODE_RETURN&&(e.key.mod&SDL_KMOD_ALT);
            bool pressed=(b.kind==Bind::Key&&e.type==SDL_EVENT_KEY_DOWN&&!e.key.repeat&&!host_fullscreen&&b.code==e.key.scancode)
                ||(b.kind==Bind::Mouse&&e.type==SDL_EVENT_MOUSE_BUTTON_DOWN&&b.code==e.button.button)
                ||(b.kind==Bind::Pad&&e.type==SDL_EVENT_GAMEPAD_BUTTON_DOWN&&b.code==e.gbutton.button);
            if(pressed)pulse_until[i]=now+100000000; // 100 ms, no repeat injection
        }
    }
    if(e.type==SDL_EVENT_MOUSE_WHEEL){int a=e.wheel.y>0?wheel_up:wheel_down;if(a>=0)pulse_until[unsigned(a)]=now+100000000;}
    if(e.type==SDL_EVENT_KEY_DOWN && direction_key(e.key.scancode))cursor.relative();
    if(e.type==SDL_EVENT_GAMEPAD_BUTTON_DOWN && e.gbutton.button>=SDL_GAMEPAD_BUTTON_DPAD_UP && e.gbutton.button<=SDL_GAMEPAD_BUTTON_DPAD_RIGHT)cursor.relative();
    if(e.type==SDL_EVENT_GAMEPAD_AXIS_MOTION && (e.gaxis.axis==SDL_GAMEPAD_AXIS_LEFTX || e.gaxis.axis==SDL_GAMEPAD_AXIS_LEFTY)
        && std::abs(e.gaxis.value/32768.f)>stick_deadzone)cursor.relative();
    // Game cancellation must not invoke an unrelated host Escape shortcut.
    // Keep Alt+Enter and all non-game host shortcuts available.
    if(e.type==SDL_EVENT_KEY_DOWN && !(e.key.mod&(SDL_KMOD_ALT|SDL_KMOD_CTRL))) {
        for(auto& list:bindings)for(auto b:list)if(b.kind==Bind::Key && b.code==e.key.scancode)return 1;
    }
    return 0;
}
int dune_input_capture(uint16_t *buttons) {
    initialize();if(!native_mode)return 0;
    Actions actions{};const bool* keys=SDL_GetKeyboardState(nullptr);
    uint64_t now=SDL_GetTicksNS();
    auto mouse=SDL_GetMouseState(nullptr,nullptr);
    if(focused)for(unsigned i=0;i<ActionCount;i++) {
        for(auto b:bindings[i]) {
            if(b.kind==Bind::Key) {
                bool host_fullscreen=b.code==SDL_SCANCODE_RETURN&&(SDL_GetModState()&SDL_KMOD_ALT);
                actions[i]=actions[i]||(!host_fullscreen&&keys[b.code]);
            }
            else if(b.kind==Bind::Mouse)actions[i]=actions[i]||bool(mouse&SDL_BUTTON_MASK(b.code));
            else for(auto [id,pad]:pads) {
                if(b.kind==Bind::Pad)actions[i]=actions[i]||SDL_GetGamepadButton(pad,SDL_GamepadButton(b.code));
                else if(b.kind==Bind::Trigger)actions[i]=actions[i]||SDL_GetGamepadAxis(pad,SDL_GamepadAxis(b.code))>16384;
            }
        }
        if(now<pulse_until[i])actions[i]=true;
    }
    float dt=previous_time?float(now-previous_time)*1e-9f:0.f;
    previous_time=now;dt=std::clamp(dt,0.f,.05f);
    float sx=0,sy=0;
    if(focused)for(auto [id,pad]:pads) {
        float x=deadzone_axis(SDL_GetGamepadAxis(pad,SDL_GAMEPAD_AXIS_LEFTX)/32768.f,stick_deadzone);
        float y=deadzone_axis(SDL_GetGamepadAxis(pad,SDL_GAMEPAD_AXIS_LEFTY)/32768.f,stick_deadzone);
        if(std::abs(x)>std::abs(sx))sx=x;
        if(std::abs(y)>std::abs(sy))sy=y;
    }
    int cx=0,cy=0;bool gameplay=dune_cursor_get(&cx,&cy)!=0;
    if(!gameplay){
        cursor.mouse_dirty=false;remainder_x=remainder_y=0;
        // Frontend has a menu selection, not gameplay cursor coordinates.
        actions[unsigned(GameAction::CursorLeft)]|=sx<-.4f;
        actions[unsigned(GameAction::CursorRight)]|=sx>.4f;
        actions[unsigned(GameAction::CursorUp)]|=sy<-.4f;
        actions[unsigned(GameAction::CursorDown)]|=sy>.4f;
    }
    if(gameplay && focused) {
        Point position;
        if(cursor.consume_absolute(position)){dune_cursor_set(int(position.x),int(position.y));remainder_x=remainder_y=0;}
        else if(cursor.owner==CursorOwner::Relative) {
            remainder_x+=sx*stick_speed*dt;remainder_y+=sy*stick_speed*dt;
            int dx=int(remainder_x),dy=int(remainder_y);remainder_x-=dx;remainder_y-=dy;
            if(dx||dy)dune_cursor_set(cx+dx,cy+dy);
        }
        if(cursor.owner==CursorOwner::Mouse)
            for(unsigned i=unsigned(GameAction::CursorUp);i<=unsigned(GameAction::CursorRight);i++)actions[i]=false;
    }
    *buttons=original_buttons(actions);return 1;
}
