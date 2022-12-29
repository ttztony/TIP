import os
import torch
from imwatermark import WatermarkEncoder

from ldm.util import instantiate_from_config
from ldm.models.diffusion.ddim import DDIMSampler
from ldm.models.diffusion.plms import PLMSSampler
from ldm.models.diffusion.dpm_solver import DPMSolverSampler

import cv2
from PIL import Image
import numpy as np

import hydra
from omegaconf import DictConfig, OmegaConf

from einops import rearrange
from torchvision.utils import make_grid
from pytorch_lightning import seed_everything
from torch import autocast
from contextlib import nullcontext

from tqdm import tqdm, trange

def load_model_from_config(config, ckpt, verbose=False):
    print(f"Loading model from {ckpt}")
    pl_sd = torch.load(ckpt, map_location="cpu")
    if "global_step" in pl_sd:
        print(f"Global Step: {pl_sd['global_step']}")
    sd = pl_sd["state_dict"]
    model = instantiate_from_config(config.model)
    m, u = model.load_state_dict(sd, strict=False)
    if len(m) > 0 and verbose:
        print("missing keys:")
        print(m)
    if len(u) > 0 and verbose:
        print("unexpected keys:")
        print(u)

    model.cuda()
    model.eval()
    return model

def put_watermark(img, wm_encoder=None):
    if wm_encoder is not None:
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        img = wm_encoder.encode(img, 'dwtDct')
        img = Image.fromarray(img[:, :, ::-1])
    return img

class Image_Generation(object):
    def __init__(self, opt, config, outpath) -> None:
        super().__init__()
        self.opt = opt
        self.config = config
        self.outpath = outpath
        self.model = load_model_from_config(config, f"{config.model.ckpt}")
        # model = hydra.utils.instantiate(cfg.model)

        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.model = self.model.to(self.device)
        
    def generate_image(self, opt, data, task_start_idx_list=[], step_idx=-1):
        model = self.model
        opt = self.opt
        if opt.plms:
            sampler = PLMSSampler(model)
        elif opt.dpm:
            sampler = DPMSolverSampler(model)
        else:
            sampler = DDIMSampler(model)

        print("Creating invisible watermark encoder (see https://github.com/ShieldMnt/invisible-watermark)...")
        wm = "SDV2"
        wm_encoder = WatermarkEncoder()
        wm_encoder.set_watermark('bytes', wm.encode('utf-8'))

        batch_size = opt.n_samples
        n_rows = opt.n_rows if opt.n_rows > 0 else batch_size

        sample_path = os.path.join(self.outpath, opt.data_type, "bridge" if opt.use_bridge else "origin", opt.task+("_w_task_hint" if opt.use_task_hint else "")) # os.path.join(outpath, "samples")
        os.makedirs(sample_path, exist_ok=True)
        sample_count = 0
        task_count = -1
        step_count = 0
        all_step_count = 0
        base_count = len(os.listdir(sample_path))
        # grid_count = len(os.listdir(outpath)) - 1

        start_code = None
        if opt.fixed_code:
            start_code = torch.randn([opt.n_samples, opt.C, opt.H // opt.f, opt.W // opt.f], device=self.device)

        precision_scope = autocast if opt.precision == "autocast" else nullcontext
        with torch.no_grad(), \
            precision_scope("cuda"), \
            model.ema_scope():
                for n in trange(opt.n_iter, desc="Sampling"):
                    for prompts in tqdm(data, desc="data"):
                        uc = None
                        if opt.scale != 1.0:
                            uc = model.get_learned_conditioning(batch_size * [""])
                        if isinstance(prompts, tuple):
                            prompts = list(prompts)
                        c = model.get_learned_conditioning(prompts)
                        shape = [opt.C, opt.H // opt.f, opt.W // opt.f]
                        samples, _ = sampler.sample(S=opt.steps,
                                                        conditioning=c,
                                                        batch_size=opt.n_samples,
                                                        shape=shape,
                                                        verbose=False,
                                                        unconditional_guidance_scale=opt.scale,
                                                        unconditional_conditioning=uc,
                                                        eta=opt.ddim_eta,
                                                        x_T=start_code)

                        x_samples = model.decode_first_stage(samples)
                        x_samples = torch.clamp((x_samples + 1.0) / 2.0, min=0.0, max=1.0)

                        for x_sample, x_prompt in zip(x_samples, prompts):
                            if all_step_count in task_start_idx_list or step_idx == 0:
                                task_count += 1
                                all_samples = list()
                                step_count = 0
                                sample_path = os.path.join(self.outpath, opt.data_type, "bridge" if opt.use_bridge else "origin", opt.task+("_w_task_hint" if opt.use_task_hint else ""), "task_{}".format(task_count))
                                os.makedirs(sample_path, exist_ok=True)

                            all_samples.append(x_sample)
                            x_sample = 255. * rearrange(x_sample.cpu().numpy(), 'c h w -> h w c')
                            img = Image.fromarray(x_sample.astype(np.uint8))
                            img = put_watermark(img, wm_encoder)
                            # img.save(os.path.join(sample_path, f"{base_count:05}.png"))
                            if step_idx > 0 and len(task_start_idx_list) == 0:
                                img.save(os.path.join(sample_path, f"step_{step_idx}.png"))
                                if not opt.task in ["u-plan", "m-plan"]:
                                    with open(os.path.join(sample_path, f"step_{step_idx}.txt"), 'w') as f:
                                        f.write(f"{x_prompt}")
                            else:
                                img.save(os.path.join(sample_path, f"step_{step_count}.png"))
                                if not opt.task in ["u-plan", "m-plan"]:
                                    with open(os.path.join(sample_path, f"step_{step_count}.txt"), 'w') as f:
                                        f.write(f"{x_prompt}")

                            step_count += 1
                            all_step_count += 1 
                            base_count += 1
                            sample_count += 1
                            
                            if  opt.save_task_grid and (all_step_count in task_start_idx_list or all_step_count == len(prompts)):
                                # save previous task as grid
                                grid = torch.stack(all_samples[1:], 0)
                                grid = rearrange(grid, 'n b c h w -> (n b) c h w')
                                grid = make_grid(grid, nrow=len(all_samples)-1)

                                # to image
                                grid = 255. * rearrange(grid, 'c h w -> h w c').cpu().numpy()
                                grid = Image.fromarray(grid.astype(np.uint8))
                                grid = put_watermark(grid, wm_encoder)
                                grid.save(os.path.join(sample_path, f'task-grid-{task_count}.png'))


        print(f"Your samples are ready and waiting for you here: \n{self.outpath} \n"
            f" \nEnjoy.")
