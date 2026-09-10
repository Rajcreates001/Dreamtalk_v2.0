# Dreamtalk - Face Engine
# Extracted from MuseTalk
default_scope = 'mmpose'

custom_imports = dict(imports=['mmpose.datasets.datasets.ubody'], allow_failed_imports=False)

# runtime
default_hooks = dict(
    timer=dict(type='IterTimerHook'),
    logger=dict(type='LoggerHook', interval=50),
    param_scheduler=dict(type='ParamSchedulerHook'),
    checkpoint=dict(type='CheckpointHook', interval=10),
    sampler_seed=dict(type='DistSamplerSeedHook'),
    visualization=dict(type='PoseVisualizationHook', enable=False),
)

custom_hooks = [
    dict(
        type='PreciseBNHook',
        num_bn_batches=501,
        interval=1,
    )
]

env_cfg = dict(
    cudnn_benchmark=False,
    mp_cfg=dict(mp_start_method='fork', opencv_num_threads=0),
    dist_cfg=dict(backend='nccl'),
)

log_level = 'INFO'
load_from = None
resume = False
