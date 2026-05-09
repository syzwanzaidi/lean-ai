STEPS = [
    {
        "id": 1,
        "title": "LED Module Installation",
        "instruction": "Insert the LED Module into the LED Housing.",
        "verification_goal": "The LED Module must be inserted into the LED Housing. The outer diffuser cover and mounting base are not required yet.",
        "must_have": [
            "LED Module is visible",
            "LED Housing is attached",
            "LED Module is inserted into the LED Housing"
        ],
        "must_not_require": [
            "Outer Diffuser Cover",
            "Mounting Base",
            "Nut and bolt"
        ],
        "reference_images": [
            "references/step_1_a.jpg",
            "references/step_1_b.jpg",
            "references/step_1_c.jpg",
            "references/step_1_d.jpg",
        ],
    },
    {
        "id": 2,
        "title": "Internal Diffuser Spacer Installation",
        "instruction": "Attach the Internal Diffuser Spacer to the LED Module assembly.",
        "verification_goal": "The internal diffuser spacer/holder must be attached around the LED strip. Do not reject because of small angle or cable position differences.",
        "must_have": [
            "LED Module is visible",
            "LED Housing is attached",
            "Internal Diffuser Spacer is attached"
        ],
        "must_not_require": [
            "Outer Diffuser Cover",
            "Mounting Base",
            "Nut and bolt"
        ],
        "reference_images": [
            "references/step_2_a.jpg",
            "references/step_2_b.jpg",
            "references/step_2_c.jpg",
            "references/step_2_d.jpg",
        ],
    },
    {
        "id": 3,
        "title": "Outer Diffuser Cover Installation",
        "instruction": "Close the assembly using the Outer Diffuser Cover.",
        "verification_goal": "The transparent/white cylindrical Outer Diffuser Cover must cover the internal LED module and spacer. If the LED strip/spacer is still exposed, this step is wrong.",
        "must_have": [
            "Outer Diffuser Cover is installed",
            "LED strip is covered",
            "Assembly looks like a closed cylinder"
        ],
        "must_not_require": [
            "Mounting Base",
            "Nut and bolt"
        ],
        "reference_images": [
            "references/step_3_a.jpg",
            "references/step_3_b.jpg",
        ],
    },
    {
        "id": 4,
        "title": "Mounting Base Installation",
        "instruction": "Attach the completed lamp body to the flat round Mounting Base using the nut and bolt.",
        "verification_goal": "The completed lamp body must be attached to the large flat round mounting base/plate. The base has a flat circular plate with screw holes. If only the small circular joint/bracket is visible, this is NOT correct.",
        "must_have": [
            "Closed lamp body",
            "Large flat round mounting base/plate is attached",
            "Mounting base has visible screw holes",
            "Lamp body is connected to the mounting base"
        ],
        "must_not_require": [],
        "reference_images": [
            "references/step_4_a.jpg",
            "references/step_4_b.jpg",
        ],
    },
    {
        "id": 5,
        "title": "Assembly Completed",
        "instruction": "Assembly completed successfully.",
        "verification_goal": "The lamp assembly is complete.",
        "must_have": [],
        "must_not_require": [],
        "reference_images": [],
    },
]