# Local visual grouping

Wallpaper Pro uses the MIT-licensed [Xenova CLIP ViT-B/32 ONNX model](https://huggingface.co/Xenova/clip-vit-base-patch32), converted from [OpenAI CLIP ViT-B/32](https://huggingface.co/openai/clip-vit-base-patch32), through [Transformers.js](https://github.com/huggingface/transformers.js) and ONNX Runtime.

Dependencies are installed separately into the user's Wallpaper Pro data directory, with their own license files. Model weights are downloaded into `context-models` during explicit setup; they are not shipped in this repository. Normal analysis disables remote model access and reads local thumbnail files only. No wallpaper images are uploaded.

The model supplies visual embeddings. Subject labels use a fixed set of scene/object prompts, never filename keywords. Whole-image and center views are blended; extra edge views cover wide panoramas and tall images. Similarity scores are not calibrated probabilities. Labels are suggestions, and close/low-score results are marked uncertain.

The color-first order uses 30-degree hue families, then suggested subjects, then a deterministic visual-neighbor route within each subject. Dark, gray, and light neutral families follow colored families. Fine hue and brightness break ties. Cached embeddings allow prompt refinements and neighborhood recalculation without decoding every image again.
