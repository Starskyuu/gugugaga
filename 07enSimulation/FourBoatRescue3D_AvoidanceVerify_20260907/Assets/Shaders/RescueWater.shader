Shader "Custom/RescueWater"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (0.03, 0.42, 0.62, 1)
        _DeepColor ("Deep Color", Color) = (0.01, 0.22, 0.40, 1)
        _FoamColor ("Foam Color", Color) = (0.85, 0.95, 1.0, 1)
        _WaveAmplitude ("Wave Amplitude", Range(0.0, 0.008)) = 0.0016
        _WaveTime ("Wave Time", Float) = 0
        _FoamAmount ("Foam Amount", Range(0.0, 1.0)) = 0.6
        _SpecStrength ("Specular Strength", Range(0.0, 2.0)) = 0.9
        _Shininess ("Shininess", Range(4.0, 512.0)) = 120
        _EdgeBlend ("Edge Blend", Range(0.0, 1.0)) = 0.45
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        LOD 200

        Pass
        {
            Name "UniversalForward"
            Tags { "LightMode" = "UniversalForward" }

            ZWrite On
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float4 _DeepColor;
                float4 _FoamColor;
                float _WaveAmplitude;
                float _WaveTime;
                float _FoamAmount;
                float _SpecStrength;
                float _Shininess;
                float _EdgeBlend;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float waveHeight : TEXCOORD2;
                float fogFactor : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            // Must stay in sync with WaterSystem.cs HeightAt().
            float WaveHeight(float2 pos, out float2 slope)
            {
                // Wave 1: heading 25 deg, wavelength 0.14 m, phase speed 0.30 m/s
                float2 d1 = float2(0.4226, 0.9063);
                float k1 = 44.8799;
                float w1 = 13.4640;
                float p1 = k1 * (pos.x * d1.x + pos.y * d1.y) - w1 * _WaveTime;

                // Wave 2: heading -40 deg, wavelength 0.055 m, phase speed 0.55 m/s
                float2 d2 = float2(-0.6428, 0.7660);
                float k2 = 114.2398;
                float w2 = 62.8319;
                float p2 = k2 * (pos.x * d2.x + pos.y * d2.y) - w2 * _WaveTime + 1.3;

                float a2 = _WaveAmplitude * 0.38;
                float h = _WaveAmplitude * sin(p1) + a2 * sin(p2);

                slope.x = _WaveAmplitude * k1 * d1.x * cos(p1) + a2 * k2 * d2.x * cos(p2);
                slope.y = _WaveAmplitude * k1 * d1.y * cos(p1) + a2 * k2 * d2.y * cos(p2);
                return h;
            }

            Varyings vert(Attributes input)
            {
                Varyings output;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                float2 slope;
                float3 posOS = input.positionOS.xyz;
                posOS.y += WaveHeight(posOS.xz, slope);
                float3 posWS = TransformObjectToWorld(posOS.xyz);

                output.positionWS = posWS;
                output.normalWS = normalize(float3(-slope.x, 1.0, -slope.y));
                output.waveHeight = posOS.y;
                output.positionCS = TransformWorldToHClip(posWS);
                output.fogFactor = ComputeFogFactor(output.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);

                float3 N = normalize(input.normalWS);
                float3 V = normalize(GetCameraPositionWS() - input.positionWS);

                Light mainLight = GetMainLight();
                float3 L = normalize(mainLight.direction);
                float3 H = normalize(L + V);

                float ampTotal = max(_WaveAmplitude * 1.38, 0.00001);
                float heightT = saturate((input.waveHeight + ampTotal) / (2.0 * ampTotal));

                half3 water = lerp(_DeepColor.rgb, _BaseColor.rgb, heightT);

                float ndl = saturate(dot(N, L)) * 0.5 + 0.5;
                water *= lerp(0.85, 1.15, ndl);
                water *= lerp(1.0, 0.72, _EdgeBlend * (1.0 - saturate(dot(N, V))));

                float spec = pow(saturate(dot(N, H)), _Shininess) * _SpecStrength;
                water += mainLight.color.rgb * spec;

                // Crest foam must be both high and steep. Height-only foam made
                // every wave crest a large glowing white tile in top-down view.
                float crest = smoothstep(0.68, 0.96, heightT);
                float steepness = smoothstep(0.025, 0.16, 1.0 - N.y);
                float foam = crest * steepness * _FoamAmount;
                water = lerp(water, _FoamColor.rgb, foam);

                float fresnel = pow(1.0 - saturate(dot(N, V)), 4.0);
                water += lerp(float3(0.01, 0.03, 0.04), _FoamColor.rgb * 0.12, fresnel);

                water = MixFog(water, input.fogFactor);
                return half4(water, 1.0);
            }
            ENDHLSL
        }
    }
}
