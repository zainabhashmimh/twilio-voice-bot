from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

model = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

def query_llm(prompt):
    result = pipe(prompt, max_new_tokens=100)[0]["generated_text"]
    return result
