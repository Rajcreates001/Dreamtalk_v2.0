# Adapted from IndicF5 (AI4Bharat/IndicF5) - MIT License
import argparse
import os
import shutil
import torch

from cached_path import cached_path
from ..model import CFM, UNetT, DiT, Trainer
from ..model.utils import get_tokenizer
from ..model.dataset import load_dataset
from importlib.resources import files

from accelerate import Accelerator

accelerator = Accelerator()
print(f"Using mixed precision: {accelerator.mixed_precision}")

target_sample_rate = 24000
n_mel_channels = 100
hop_length = 256
win_length = 1024
n_fft = 1024
mel_spec_type = "vocos"


def parse_args():
    parser = argparse.ArgumentParser(description="Train CFM Model")

    parser.add_argument(
        "--exp_name", type=str, default="F5TTS_Base", choices=["F5TTS_Base", "E2TTS_Base"], help="Experiment name"
    )
    parser.add_argument("--dataset_name", type=str, default="Emilia_ZH_EN", help="Name of the dataset to use")
    parser.add_argument("--learning_rate", type=float, default=1e-5, help="Learning rate for training")
    parser.add_argument("--batch_size_per_gpu", type=int, default=3200, help="Batch size per GPU")
    parser.add_argument(
        "--batch_size_type", type=str, default="frame", choices=["frame", "sample"], help="Batch size type"
    )
    parser.add_argument("--max_samples", type=int, default=64, help="Max sequences per batch")
    parser.add_argument("--grad_accumulation_steps", type=int, default=1, help="Gradient accumulation steps")
    parser.add_argument("--max_grad_norm", type=float, default=1.0, help="Max gradient norm for clipping")
    parser.add_argument("--epochs", type=int, default=700, help="Number of training epochs")
    parser.add_argument("--num_warmup_updates", type=int, default=1500, help="Warmup steps")
    parser.add_argument("--save_per_updates", type=int, default=4000, help="Save checkpoint every X steps")
    parser.add_argument("--last_per_steps", type=int, default=40000, help="Save last checkpoint every X steps")
    parser.add_argument("--finetune", type=bool, default=True, help="Use Finetune")
    parser.add_argument("--pretrain", type=str, default=None, help="the path to the checkpoint")
    parser.add_argument(
        "--tokenizer", type=str, default="pinyin", choices=["pinyin", "char", "custom"], help="Tokenizer type"
    )
    parser.add_argument(
        "--tokenizer_path",
        type=str,
        default=None,
        help="Path to custom tokenizer vocab file (only used if tokenizer = 'custom')",
    )
    parser.add_argument(
        "--log_samples",
        type=bool,
        default=False,
        help="Log inferenced samples per ckpt save steps",
    )
    parser.add_argument("--logger", type=str, default=None, choices=["wandb", "tensorboard"], help="logger")
    parser.add_argument(
        "--bnb_optimizer",
        type=bool,
        default=False,
        help="Use 8-bit Adam optimizer from bitsandbytes",
    )
    parser.add_argument("--ckpt_dir", required=True, type=str)
    parser.add_argument("--data_dir", required=True, type=str)
    parser.add_argument("--wandb_resume_id", type=str, default=None)
    parser.add_argument("--resume", type=bool, default=False, help="Resume Finetune")

    return parser.parse_args()


def main():
    args = parse_args()

    checkpoint_path = args.ckpt_dir

    if args.exp_name == "F5TTS_Base":
        wandb_resume_id = args.wandb_resume_id
        print("wandb resume id is: ", wandb_resume_id)
        model_cls = DiT
        model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)

    if args.finetune and not args.resume:
        if not os.path.isdir(checkpoint_path):
            os.makedirs(checkpoint_path, exist_ok=True)

        file_checkpoint = os.path.join(checkpoint_path, 'model_last.pt')

    tokenizer = args.tokenizer
    if tokenizer == "custom":
        if not args.tokenizer_path:
            raise ValueError("Custom tokenizer selected, but no tokenizer_path provided.")
        tokenizer_path = args.tokenizer_path
    else:
        tokenizer_path = args.dataset_name

    vocab_char_map, vocab_size = get_tokenizer(tokenizer_path, tokenizer)

    print("\nvocab : ", vocab_size)
    print("\nvocoder : ", mel_spec_type)

    mel_spec_kwargs = dict(
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        n_mel_channels=n_mel_channels,
        target_sample_rate=target_sample_rate,
        mel_spec_type=mel_spec_type,
    )

    model = CFM(
        transformer=model_cls(**model_cfg, text_num_embeds=vocab_size, mel_dim=n_mel_channels),
        mel_spec_kwargs=mel_spec_kwargs,
        vocab_char_map=vocab_char_map,
    )

    trainer = Trainer(
        model,
        args.epochs,
        args.learning_rate,
        num_warmup_updates=args.num_warmup_updates,
        save_per_updates=args.save_per_updates,
        checkpoint_path=checkpoint_path,
        batch_size=args.batch_size_per_gpu,
        batch_size_type=args.batch_size_type,
        max_samples=args.max_samples,
        grad_accumulation_steps=args.grad_accumulation_steps,
        max_grad_norm=args.max_grad_norm,
        logger=args.logger,
        wandb_project=args.dataset_name,
        wandb_run_name=args.exp_name,
        wandb_resume_id=wandb_resume_id,
        log_samples=args.log_samples,
        last_per_steps=args.last_per_steps,
        bnb_optimizer=args.bnb_optimizer,
    )

    train_dataset = load_dataset(args.dataset_name, tokenizer, mel_spec_kwargs=mel_spec_kwargs, data_dir=args.data_dir)

    trainer.train(
        train_dataset,
        resumable_with_seed=666,
        num_workers=16
    )


if __name__ == "__main__":
    main()
