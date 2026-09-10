# Dreamtalk - Face Engine
# Extracted from MuseTalk
type = 'TopDownPoseEstimator'

data_preprocessor = dict(
    type='PoseDataPreprocessor',
    mean=[123.675, 116.28, 103.53],
    std=[58.395, 57.12, 57.375],
    bgr_to_rgb=True,
)

# model settings
model = dict(
    type='TopDownPoseEstimator',
    backbone=dict(
        type='CSPNeXt',
        arch='P5',
        expand_ratio=0.5,
        deepen_factor=1.,
        widen_factor=1.,
        channel_attention=True,
        norm_cfg=dict(type='SyncBN'),
        act_cfg=dict(type='SiLU', inplace=True),
        init_cfg=dict(
            type='Pretrained',
            prefix='backbone.',
            checkpoint='https://download.openmmlab.com/mmpose/v1/'
            'wholebody_2d_keypoint/rtmpose/ubody/rtmpose-l_simcc-ucoco_dw-animal-rgb_pt-e370-fl-acc.pth'
        ),
    ),
    head=dict(
        type='RTMWHead',
        in_channels=1024,
        out_channels=133,
        input_feat_index=0,
        simcc_split_ratio=2,
        final_layer_kernel_size=7,
        loss=dict(
            type='KLDiscretLoss',
            use_target_weight=True,
            beta=10.,
            label_soft=True,
        ),
        decoder=dict(
            type='SimCCLabel',
            input_size=(288, 384),
            smoothing_type='standard',
            sigma=6.,
            simcc_split_ratio=2,
            label_file_path='',
            normalize_type='label_smooth',
        ),
    ),
    test_cfg=dict(
        flip_test=True,
        shift_coords=False,
        shift_heatmap=False,
    ),
)
