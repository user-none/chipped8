#version 450

layout(location = 0) out vec2 v_uv;
layout(set = 0, binding = 1) uniform Scale {
    vec2 scale;
};

void main() {
    const vec2 positions[4] = vec2[](
        vec2(-1.0, -1.0),
        vec2( 1.0, -1.0),
        vec2(-1.0,  1.0),
        vec2( 1.0,  1.0)
    );
    const vec2 uvs[4] = vec2[](
        vec2(0.0, 1.0),
        vec2(1.0, 1.0),
        vec2(0.0, 0.0),
        vec2(1.0, 0.0)
    );
    gl_Position = vec4(positions[gl_VertexIndex] * scale, 0.0, 1.0);
    v_uv = uvs[gl_VertexIndex];
}
