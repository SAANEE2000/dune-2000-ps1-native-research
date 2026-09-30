#pragma once
#include <stdint.h>
struct SDL_Window;
struct SDL_Renderer;
union SDL_Event;
void dune_input_initialize(SDL_Window *window);
int dune_input_event(const SDL_Event *event);
void dune_input_viewport(SDL_Window *window,SDL_Renderer *renderer,
                         float x,float y,float width,float height,int logical_w,int logical_h);
int dune_input_capture(uint16_t *buttons);
int dune_cursor_get(int *x,int *y);
void dune_cursor_set(int x,int y);
