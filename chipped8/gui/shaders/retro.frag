#version 450

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_color;

layout(set = 0, binding = 0) uniform sampler2D tex;

layout(std140, set = 0, binding = 2) uniform Uniforms {
    float time;
    vec2 resolution;

    int enable_scanlines;
    int enable_glow;
    int enable_barrel;
    int enable_chromatic;
    int enable_vignette;
    int enable_noise;
    int enable_flicker;
    int enable_quantize;
    int enable_interlace;
    int enable_mask;
    int enable_wrap;
    int enable_scan_delay;
};

float rand(vec2 co) {
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

vec3 phosphorGlow(sampler2D tex, vec2 uv, vec2 resolution) {
    vec3 col = vec3(0.0);
    float total = 0.0;
    float radius = 1.5 / resolution.y;

    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            vec2 offset = vec2(float(x), float(y)) * radius;
            float weight = 1.0 - length(offset) / radius;
            col += texture(tex, uv + offset).rgb * weight;
            total += weight;
        }
    }
    return col / total;
}

vec2 barrelDistortion(vec2 uv) {
    vec2 cc = uv - 0.5;
    float r2 = dot(cc, cc);
    return uv + cc * r2 * 0.15;
}

vec2 wrapDistortion(vec2 uv) {
    uv = mod(uv * vec2(1.01, 1.01), 1.0);
    return uv;
}

void main() {
    vec2 uv = v_uv;

    if (enable_wrap == 1)
        uv = wrapDistortion(uv);

    if (enable_barrel == 1)
        uv = barrelDistortion(uv);

    // Flicker / jitter
    if (enable_flicker == 1) {
        float jitter = 0.002;  // increase magnitude
        float flickerSpeed = 60.0;  // flicker frequency in Hz
        float flickerTime = fract(time * flickerSpeed); // cycles quickly

        // Add some flicker intensity modulated by time to make it blink
        float flickerIntensity = smoothstep(0.4, 0.6, flickerTime);

        uv += vec2(rand(vec2(time * 100.0, uv.y)), rand(vec2(uv.x, time * 100.0))) * jitter * flickerIntensity;
    }

    // Chromatic aberration
    vec3 color;
    if (enable_chromatic == 1) {
        float ca = 0.003;
        color.r = texture(tex, uv + vec2(ca, 0)).r;
        color.g = texture(tex, uv).g;
        color.b = texture(tex, uv - vec2(ca, 0)).b;
    } else {
        color = texture(tex, uv).rgb;
    }

    // Scanline delay / rolling scan
    if (enable_scan_delay == 1) {
        float pixelX = 1.0 / resolution.x;
        float pixelY = 1.0 / resolution.y;

        float bandHeight = 0.01;                        // height of vertical band (~2% of screen)
        float speed = 60.0 / 60.0;                      // 1 vertical sweep per second at 60Hz
        float bandCenter = mod(time * speed, 1.0);     // moves from bottom to top

        // Distance from current pixel to band center on Y axis
        float dist = abs(uv.y - bandCenter);

        // Band intensity: 1 at center, fading smoothly to 0 outside bandHeight
        float intensity = smoothstep(bandHeight, 0.0, dist);

        // Offset UV to the right for pixels inside the band
        vec2 offsetUV = uv + vec2(pixelX * 0.5, 0.0);

        // Sample base color and right-offset color for blur
        vec3 base = texture(tex, uv).rgb;
        vec3 shifted = texture(tex, offsetUV).rgb;

        // Blend base and shifted for slight horizontal blur
        vec3 blurred = mix(base, shifted, 0.5);

        // Brighten the band area, blend between base and blurred+brightened color
        color = mix(base, blurred * (1.0 + 0.1 * intensity), intensity);
    }

    // Interlace
    if (enable_interlace == 1) {
        if (mod(floor(uv.y * resolution.y), 2.0) < 1.0) {
            color *= 0.9;
        }
    }

    // Scanlines
    if (enable_scanlines == 1) {
        float scanline = sin(uv.y * 800.0);
        float factor = 0.1 * scanline;
        color += vec3(factor);
    }

    // Shadow mask / slot mask
    if (enable_mask == 1) {
        float slotPos = fract(uv.x * resolution.x / 3.0);

        float redStripe = smoothstep(0.0, 0.15, slotPos) * smoothstep(0.33, 0.18, slotPos);
        float greenStripe = smoothstep(0.33, 0.48, slotPos) * smoothstep(0.66, 0.51, slotPos);
        float blueStripe = smoothstep(0.66, 0.81, slotPos) * smoothstep(1.0, 0.84, slotPos);

        vec3 mask = vec3(redStripe, greenStripe, blueStripe);

        color *= mix(vec3(1.0), mask, 0.15);  // dim background 100%, blend 15%
    }

    // Noise
    if (enable_noise == 1) {
        float n = (rand(uv * resolution + time * 100.0) - 0.5) * 0.10;
        color += n;
    }

    // Color quantization
    if (enable_quantize == 1) {
        color = floor(color * 5.0) / 5.0;
    }

    // Glow / bloom
    if (enable_glow == 1) {
        vec3 glow = phosphorGlow(tex, uv, resolution);
        color += glow * 0.07;
    }

    // Vignette
    if (enable_vignette == 1) {
        float d = distance(uv, vec2(0.5));
        color *= smoothstep(0.8, 0.4, d);
    }

    // Final output
    color = clamp(color, 0.0, 1.0);
    //color = pow(color, vec3(1.0 / 2.2)); // gamma correction
    out_color = vec4(color, 1.0);
}
