shader_type canvas_item;
// A light retro-CRT pass over the whole screen: one scanline per game pixel row,
// a faint RGB mask, a soft vignette and a slight phosphor lift. It never bends or
// blurs the picture, so every game pixel stays crisp and square.

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest, repeat_disable;
uniform vec2 game_res = vec2(320.0, 180.0);
uniform float scanline : hint_range(0.0, 1.0) = 0.26;
uniform float vignette : hint_range(0.0, 1.0) = 0.38;
uniform float mask : hint_range(0.0, 0.3) = 0.06;
uniform float lift : hint_range(0.0, 0.2) = 0.04;

void fragment() {
	vec3 c = texture(screen_tex, SCREEN_UV).rgb;
	// Scanline: the lower part of every game-pixel row is darker.
	float row = fract(UV.y * game_res.y);
	float dark = smoothstep(0.45, 1.0, row);
	c *= 1.0 - scanline * dark;
	// Aperture mask: a hint of red / green / blue by game column.
	float col = fract(UV.x * game_res.x * 3.0 / 3.0);
	vec3 tint = vec3(1.0 - mask) + mask * vec3(step(col, 0.33), step(0.33, col) * step(col, 0.66), step(0.66, col)) * 3.0;
	c *= tint;
	// Vignette toward the corners.
	vec2 d = UV - vec2(0.5);
	c *= 1.0 - vignette * dot(d, d) * 1.7;
	c += lift * c * c;
	COLOR = vec4(c, 1.0);
}
