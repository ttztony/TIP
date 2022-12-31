# MPP
Multimodal-Procedural-Planning

## Installation

```
git clone --recursive git@github.com:YujieLu10/MPP.git
cd MPP
conda create -n mpp
conda activate mpp
<!-- conda install pytorch==1.12.1 torchvision==0.13.1 -c pytorch -->
conda install pytorch torchvision torchaudio pytorch-cuda=11.7 -c pytorch -c nvidia
pip install transformers==4.19.2 diffusers invisible-watermark
pip install -e .
pip install -r requirements.txt
```

## Data
### WikiHow
#### Crawling @ Pan

#### Curation

#### Re-purposing

### RecipeQA: A Challenge Dataset for Multimodal Comprehension of Cooking Recipes
#### Downloading
https://aclanthology.org/D18-1166.pdf

#### Re-purposing


### WinoGround (maybe a little weird to use this)


## Zero-shot Planning
<!-- - c-plan: multimodal procedural planning, llm and t2i model will seperately generating close-loop procedural planning -->

- m-plan: multimodal procedural planning, llm and t2i model will collaboratively generating procedural planning (task->textual plan->t2i with bridge for visual plan->revise textual plan for better xx?)

- u-plan: unimodal procedural planning that seperately plan in textual and visual space (in mpp, it means first use llm to generate textual plan, and then use t2i model to visualize as visual plan)

- t(v)gt-u-plan: visual procedural planning with ground truth textual procedural plans, aka. generating visual plans directly using ground truth textual plan (textual procedural planning with ground truth visual procedural plans, aka. generating textual plans directly using ground truth visual plan)

<!-- - t(v)gt-m-plan: more like text to image generation with temporal dimension (more like image captioning with temporal dimension) -->

```
# submodules/stablediffusion
# txt2img applied over wikihow example
python scripts/txt2img.py --ckpt /share/edc/home/yujielu/MPP_data/v2-1_512-ema-pruned.ckpt --config configs/stable-diffusion/v2-inference.yaml --H 512 --W 512 --outdir /share/edc/home/yujielu/MPP_data/wikihow/output_example --task tgt-v-plan --file_type json --data_type wikihow

# MPP root
# unify command
CUDA_VISIBLE_DEVICES=4 python planning.py --task tgt-u-plan
CUDA_VISIBLE_DEVICES=4 python planning.py --task vgt-u-plan
CUDA_VISIBLE_DEVICES=4 python planning.py --task u-plan
CUDA_VISIBLE_DEVICES=4 python planning.py --task m-plan
```

## Caption Generation
```
CUDA_VISIBLE_DEVICES=7 python preprocessors/generate_caption.py --source groundtruth_input
CUDA_VISIBLE_DEVICES=7 python preprocessors/generate_caption.py --source experiment_output
```

## Evaluation

```
CUDA_VISIBLE_DEVICES=7 python planning.py --eval --data_type wikihow --eval_task all
```

## Plan Grid Visualization
```
CUDA_VISIBLE_DEVICES=7 python amt_platform/generate_plan_grid.py --source groundtruth_input
```