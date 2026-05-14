from openai_verifier import verify_step

result = verify_step(
    reference_image_path="references/step_1.jpg",
    current_image_path="references/step_1.jpg",
    instruction="Take the LED Module from Basket 1 and the LED Housing from Basket 2. Insert the LED Module into the LED Housing and secure it using the screw from Basket 6."
)

print(result)