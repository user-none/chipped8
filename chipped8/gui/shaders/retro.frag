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
    int enable_pixel_borders;
    int enable_edge_glow;
    int enable_signal_tearing;
    int enable_channel_shift;
    int enable_blocky_artifacts;
    int enable_temporal_shimmer;
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

vec2 temporalShimmer(vec2 uv, float time) {
    float strength = 0.0025;          // very subtle offset
    float speed = 1.2;
    float scale = 15.0;

    // Use time + uv-based random seed to jitter offsets smoothly
    float jitterX = (rand(uv * scale + vec2(time * speed, 0.0)) - 0.5) * strength;
    float jitterY = (rand(uv * scale + vec2(0.0, time * speed)) - 0.5) * strength;

    return clamp(uv + vec2(jitterX, jitterY), 0.0, 1.0);
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

    // Temporal shimmer
    if (enable_temporal_shimmer == 1)
        uv = temporalShimmer(uv, time);

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
        float scanline = sin(uv.y * resolution.y * 3.14159) * 0.015;
        color.rgb -= scanline;
    }

    // Scanlines
    if (enable_scanlines == 1) {
        float scanline = 1.0 + 0.1 * sin(uv.y * 800.0);  // Ranges from 0.9 to 1.1
        color.rgb *= scanline;
    }

    // Shadow mask / slot mask
    if (enable_mask == 1) {
        float slotPos = fract(uv.x * resolution.x / 3.0);

        // Use hard stripes or controlled softness
        float redStripe   = smoothstep(0.00, 0.05, slotPos) * smoothstep(0.30, 0.25, slotPos);
        float greenStripe = smoothstep(0.33, 0.38, slotPos) * smoothstep(0.63, 0.58, slotPos);
        float blueStripe  = smoothstep(0.66, 0.71, slotPos) * smoothstep(0.96, 0.91, slotPos);

        // Assemble slot mask
        vec3 mask = vec3(redStripe, greenStripe, blueStripe);

        // Blend with full intensity and apply subtly
        color.rgb = mix(color.rgb, color.rgb * mask, 0.08); // subtle blend (8%)
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

    // Grid Overlay / Pixel Borders
    if (enable_pixel_borders == 1) {
        vec2 fragCoord = uv * resolution.xy;
        float spacing = 1.0;
        float lineWidth = 0.1;

        vec2 local = mod(fragCoord, spacing);
        float edgeX = step(spacing - lineWidth, local.x);
        float edgeY = step(spacing - lineWidth, local.y);
        float grid = max(edgeX, edgeY);

        vec3 gridColor = vec3(0.0);
        float intensity = 0.08;

        color.rgb = mix(color.rgb, gridColor, grid * intensity);
    }

    if (enable_edge_glow == 1) {
        float distLeft = uv.x;
        float distRight = 1.0 - uv.x;

        float glowWidth = 0.35; // Horizontal extent
        float verticalSpread = 0.5; // Vertical glow spread

        // Vertical falloff using a gentler curve
        float vertDist = abs(uv.y - 0.5) / verticalSpread;
        float vertFade = clamp(1.0 - vertDist * vertDist, 0.0, 1.0); // quadratic falloff

        // Horizontal edge glow intensity
        float glowLeft = (1.0 - smoothstep(0.0, glowWidth, distLeft)) * vertFade;
        float glowRight = (1.0 - smoothstep(0.0, glowWidth, distRight)) * vertFade;

        float glowFactor = max(glowLeft, glowRight);

        vec3 glowColor = vec3(1.0); // White glow (lightens without tint)
        color += glowColor * glowFactor * 0.15; // Overall glow intensity
    }

    if (enable_signal_tearing == 1) {
        // Base frequency for thin bands
        float baseFreq = 4.0;

        // Add noise-based random variation to band height (between 0.5x and 1.5x of base band height)
        float bandNoise = fract(sin(floor(uv.y * baseFreq) * 12.9898 + floor(time * 3.0)) * 43758.5453);
        float bandHeight = (0.5 + bandNoise) / baseFreq;  // varies between ~0.016 and ~0.05

        // Calculate band index with jittered UV.y
        float jitter = (fract(sin(time * 10.0) * 10000.0) - 0.5) * bandHeight * 0.5; // small vertical jitter over time
        float bandPos = uv.y + jitter;

        // Calculate band start position
        float bandIndex = floor(bandPos / bandHeight);

        // Soft band edge by using smoothstep for transition
        float bandStart = bandIndex * bandHeight;
        float edgeSoftness = bandHeight * 0.3;

        float bandMask = smoothstep(bandStart, bandStart + edgeSoftness, bandPos) * 
            (1.0 - smoothstep(bandStart + bandHeight - edgeSoftness, bandStart + bandHeight, bandPos));

        // Chance of glitch per band (keep low for fewer glitches)
        float glitchChance = 0.01 + bandNoise * 0.1;  // chance varies per band a bit

        // Slow down glitch updates: change glitches roughly every 2 seconds
        float slowTime = floor(time * 0.5);  // 0.5 = update every 2 seconds

        // Adjust timeSeed to use slowTime instead of time * 5.0
        float timeSeed = bandIndex * 13.37 + slowTime;

        // Decide if this band glitches
        float glitchRoll = fract(sin(timeSeed) * 43758.5453);

        if (glitchRoll > (1.0 - glitchChance)) {
            // Random horizontal offset with variable strength based on band noise
            float offset = fract(sin(timeSeed + uv.x * 100.0) * 12345.6789);
            float strength = (offset - 0.5) * 0.02 * (0.5 + bandNoise);

            vec2 glitchUV = uv;
            glitchUV.x += strength;

            glitchUV.x = clamp(glitchUV.x, 0.0, 1.0);

            // Blend original color and glitch color by bandMask for smooth edges
            vec3 glitchColor = texture(tex, glitchUV).rgb;
            color = mix(color, glitchColor, bandMask);
        }
    }

    if (enable_channel_shift == 1) {
        float maxShift = 0.02;   // max horizontal shift of channels
        float totalBands = 8.0;  // fewer total bands on screen
        float bandHeight = 1.0 / totalBands;  // height of each band (thin)

        float speed = 1.0;       // glitch animation speed

        // Calculate which band this UV.y belongs to
        float bandIndex = floor(uv.y / bandHeight);

        float timeSeed = bandIndex * 13.37 + floor(time * speed);

        float glitchChance = 0.15;  // chance band glitches
        float glitchRoll = fract(sin(timeSeed) * 43758.5453);

        if (glitchRoll > (1.0 - glitchChance)) {
            // Random horizontal offsets per RGB channel
            float shiftR = (fract(sin(timeSeed + 1.0) * 12345.6789) - 0.5) * maxShift;
            float shiftG = (fract(sin(timeSeed + 2.0) * 12345.6789) - 0.5) * maxShift;
            float shiftB = (fract(sin(timeSeed + 3.0) * 12345.6789) - 0.5) * maxShift;

            vec2 uvR = uv + vec2(shiftR, 0.0);
            vec2 uvG = uv + vec2(shiftG, 0.0);
            vec2 uvB = uv + vec2(shiftB, 0.0);

            uvR.x = clamp(uvR.x, 0.0, 1.0);
            uvG.x = clamp(uvG.x, 0.0, 1.0);
            uvB.x = clamp(uvB.x, 0.0, 1.0);

            color.r = texture(tex, uvR).r;
            color.g = texture(tex, uvG).g;
            color.b = texture(tex, uvB).b;
        } else {
            color = texture(tex, uv).rgb;
        }
    }

    if (enable_blocky_artifacts == 1) {
        float blockSize = 0.05;
        vec2 blockUV = floor(uv / blockSize);
        float blockSeed = dot(blockUV, vec2(37.0, 113.0));


        // === Global glitch cycle ===
        float groupCycleDuration = 11.0;  // 4s glitch + up to 7s cooldown
        float groupTimeSeed = floor(time / groupCycleDuration);

        float groupRand = fract(sin(groupTimeSeed * 12.345) * 45678.9);

        // Timing
        float glitchDuration = 4.0;
        float cooldownDuration = 3.0 + fract(groupRand * 1.7) * 4.0;  // 3–7s
        float groupStartTime = groupTimeSeed * groupCycleDuration;

        float localTime = time - groupStartTime;
        bool groupActive = localTime < glitchDuration;

        if (groupActive) {
            // Block count: 5–15
            float countSeed = fract(sin(groupTimeSeed * 77.77) * 9999.0);
            int blockCount = 5 + int(fract(sin(countSeed * 8.1234) * 11.0));  // 5–15

            // Determine if this block is active
            float blockRand = fract(sin(blockSeed * 9.13 + groupTimeSeed) * 10000.0);
            bool is_active = blockRand < float(blockCount) / 100.0;

            // Random lifetime per block: 2–4s
            float blockLife = 2.0 + fract(sin(blockSeed * 17.4567) * 10000.0) * 2.0;

            // All blocks start at 0
            float blockStart = 0.0;
            float blockEnd = blockLife;

            if (is_active && localTime >= blockStart && localTime < blockEnd) {
                float offsetX = (fract(sin(blockSeed * 1.3) * 12345.6789) - 0.5) * 0.08;
                float offsetY = (fract(sin(blockSeed * 1.7) * 98765.4321) - 0.5) * 0.08;

                vec2 glitchUV = uv + vec2(offsetX, offsetY);
                glitchUV = clamp(glitchUV, 0.0, 1.0);

                vec3 glitchColor = texture(tex, glitchUV).rgb;
                color = mix(color, glitchColor, 0.8);
            }
        }
    }

    // Final output
    color = clamp(color, 0.0, 1.0);
    out_color = vec4(color, 1.0);
}
