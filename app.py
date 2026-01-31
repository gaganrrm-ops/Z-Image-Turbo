import torch
from diffusers import DiffusionPipeline, BitsAndBytesConfig
import gradio as gr
import os

# Set HF_TRANSFER for faster downloads if available
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Model Checkpoint
MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"

print(f"Loading model: {MODEL_ID}...")

# Load the pipeline with bfloat16 and safety checker disabled
# We use trust_remote_code=True because Z-Image-Turbo uses a custom pipeline
try:
    pipe = DiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        use_safetensors=True,
        trust_remote_code=True,
        # Safety checker is explicitly disabled to meet user request for uncensored content
        safety_checker=None,
        requires_safety_checker=False 
    )
    pipe.to("cuda")
    print("Model loaded successfully on CUDA.")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Attempting with 4-bit quantization due to VRAM constraints if necessary...")
    try:
        quantization_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
        pipe = DiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            quantization_config=quantization_config,
            trust_remote_code=True,
            safety_checker=None,
            requires_safety_checker=False
        )
        print("Model loaded with 4-bit quantization.")
    except Exception as e2:
        print(f"Final error loading model: {e2}")
        exit(1)

def generate_image(prompt, negative_prompt, steps, guidance_scale, width, height, seed):
    if seed == -1:
        generator = None
    else:
        generator = torch.Generator(device="cuda").manual_seed(seed)
    
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        generator=generator
    ).images[0]
    
    return image

# Gradio Interface
with gr.Blocks(title="Z-Image-Turbo Local") as demo:
    gr.Markdown("# ⚡️ Z-Image-Turbo Local (Uncensored)")
    gr.Markdown("An efficient image generation app with safety filters disabled.")
    
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Prompt", placeholder="Enter your prompt here...", lines=3)
            negative_prompt = gr.Textbox(label="Negative Prompt", placeholder="What you don't want to see...", lines=2)
            
            with gr.Accordion("Advanced Settings", open=False):
                steps = gr.Slider(minimum=1, maximum=50, value=8, step=1, label="Inference Steps (8 is recommended for Turbo)")
                guidance_scale = gr.Slider(minimum=0.0, maximum=10.0, value=3.5, step=0.1, label="Guidance Scale")
                width = gr.Slider(minimum=256, maximum=2048, value=512, step=64, label="Width")
                height = gr.Slider(minimum=256, maximum=2048, value=512, step=64, label="Height")
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
            
            btn = gr.Button("Generate ⚡️", variant="primary")
        
        with gr.Column():
            output_image = gr.Image(label="Generated Image")
            
    btn.click(
        fn=generate_image,
        inputs=[prompt, negative_prompt, steps, guidance_scale, width, height, seed],
        outputs=output_image
    )

if __name__ == "__main__":
    demo.launch(share=False)
