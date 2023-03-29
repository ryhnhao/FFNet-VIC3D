dataset_type = 'V2XDataset'
data_root = './data/dair-v2x/DAIR-V2X/cooperative-vehicle-infrastructure/'
############## flownet_test_mode: {'FlowPred', 'OriginFeat', 'Async'} ##############
# FlowPred: Use feature flow to compensate for the temporay asynchrony 
# OriginFeat: Do not introduce the simulated temporal asychrony
# Async: Introduce the temporal asynchrony and do not use feature flow to compensate for the temporay asynchrony
data_info_train_path='./data/dair-v2x/flow_data_jsons/flow_data_info_train_2.json'
data_info_val_path='./data/dair-v2x/flow_data_jsons/flow_data_info_val_2.json'
flownet_test_mode='FlowPred' # {'FlowPred', 'OriginFeat', 'Async'}
#################################################################################### 
pretrained_basemodel='./ffnet_work_dir/pretrained-checkpoints/epoch_40.pth'
work_dir = './ffnet_work_dir/work_dir_ffnet'

class_names = ['Pedestrian', 'Cyclist', 'Car']
point_cloud_range = [0, -46.08, -3, 92.16, 46.08, 1]
voxel_size = [0.16, 0.16, 4]
l = int((point_cloud_range[3]-point_cloud_range[0])/voxel_size[0])
h = int((point_cloud_range[4]-point_cloud_range[1])/voxel_size[1])
output_shape = [h, l]
z_center_pedestrian = -0.6
z_center_cyclist = -0.6
z_center_car = -2.66

model = dict(
    type='FeatureFlowNet',
    voxel_layer=dict(
        max_num_points=100,
        point_cloud_range=point_cloud_range,
        voxel_size=voxel_size,
        max_voxels=(40000, 40000)),
    voxel_encoder=dict(
        type='PillarFeatureNet',
        in_channels=4,
        feat_channels=[64],
        with_distance=False,
        voxel_size=voxel_size,
        point_cloud_range=point_cloud_range),
    middle_encoder=dict(
        type='PointPillarsScatter', in_channels=64, output_shape=output_shape),
    backbone=dict(
        type='SECOND',
        in_channels=64,
        layer_nums=[3, 5, 5],
        layer_strides=[2, 2, 2],
        out_channels=[64, 128, 256]),
    neck=dict(
        type='SECONDFPN',
        in_channels=[64, 128, 256],
        upsample_strides=[1, 2, 4],
        out_channels=[128, 128, 128]),
    bbox_head=dict(
        type='Anchor3DHead',
        num_classes=3,
        in_channels=384,
        feat_channels=384,
        use_direction_classifier=True,
        anchor_generator=dict(
            type='Anchor3DRangeGenerator',
            ranges=[[point_cloud_range[0], point_cloud_range[1], z_center_pedestrian, point_cloud_range[3], point_cloud_range[4],
                     z_center_pedestrian],
                    [point_cloud_range[0], point_cloud_range[1], z_center_cyclist, point_cloud_range[3], point_cloud_range[4],
                    z_center_cyclist],
                    [point_cloud_range[0], point_cloud_range[1], z_center_car, point_cloud_range[3], point_cloud_range[4],
                    z_center_car]],
            sizes=[[0.6, 0.8, 1.73], [0.6, 1.76, 1.73], [1.6, 3.9, 1.56]],
            rotations=[0, 1.57],
            reshape_out=False),
        diff_rad_by_sin=True,
        bbox_coder=dict(type='DeltaXYZWLHRBBoxCoder'),
        loss_cls=dict(
            type='FocalLoss',
            use_sigmoid=True,
            gamma=2.0,
            alpha=0.25,
            loss_weight=1.0),
        loss_bbox=dict(
            type='SmoothL1Loss', beta=0.1111111111111111, loss_weight=2.0),
        loss_dir=dict(
            type='CrossEntropyLoss', use_sigmoid=False, loss_weight=0.2)),
    train_cfg=dict(
        assigner=[
            dict(
                type='MaxIoUAssigner',
                iou_calculator=dict(type='BboxOverlapsNearest3D'),
                pos_iou_thr=0.5,
                neg_iou_thr=0.35,
                min_pos_iou=0.35,
                ignore_iof_thr=-1),
            dict(
                type='MaxIoUAssigner',
                iou_calculator=dict(type='BboxOverlapsNearest3D'),
                pos_iou_thr=0.5,
                neg_iou_thr=0.35,
                min_pos_iou=0.35,
                ignore_iof_thr=-1),
            dict(
                type='MaxIoUAssigner',
                iou_calculator=dict(type='BboxOverlapsNearest3D'),
                pos_iou_thr=0.6,
                neg_iou_thr=0.45,
                min_pos_iou=0.45,
                ignore_iof_thr=-1)
        ],
        allowed_border=0,
        pos_weight=-1,
        debug=False,
        pretrained_model=pretrained_basemodel,
        data_root=data_root
    ),
    test_cfg=dict(
        use_rotate_nms=False,
        nms_across_levels=False,
        nms_thr=0.01,
        score_thr=0.2,
        min_bbox_size=0,
        nms_pre=1000,
        max_num=300,
        test_mode=flownet_test_mode,
        pretrained_model='',
        data_root=data_root
    )
)

file_client_args = dict(backend='disk')

data = dict(
    samples_per_gpu=2,
    workers_per_gpu=2,
    train=dict(
        type='RepeatDataset',
        times=2,
        dataset=dict(
            type=dataset_type,
            data_root=data_root,
            ann_file=data_info_train_path,
            split='training',
            pts_prefix='velodyne_reduced',
            pipeline=[
                dict(
                    type='LoadPointsFromFile',
                    coord_type='LIDAR',
                    load_dim=4,
                    use_dim=4,
                    sensor_view='vehicle'),
                dict(
                    type='LoadPointsFromFile',
                    coord_type='LIDAR',
                    load_dim=4,
                    use_dim=4,
                    sensor_view='infrastructure'),
                dict(
                    type='LoadAnnotations3D',
                    with_bbox_3d=True,
                    with_label_3d=True),
                # dict(type='RandomFlip3D', flip_ratio_bev_horizontal=0.5),
                # dict(
                #     type='GlobalRotScaleTrans',
                #     rot_range=[-0.78539816, 0.78539816],
                #     scale_ratio_range=[0.95, 1.05]),
                dict(
                    type='PointsRangeFilter',
                    point_cloud_range=point_cloud_range),
                dict(
                    type='ObjectRangeFilter',
                    point_cloud_range=point_cloud_range),
                # dict(type='PointShuffle'),
                dict(
                    type='DefaultFormatBundle3D',
                    class_names=class_names),
                dict(
                    type='Collect3D',
                    keys=['points', 'infrastructure_points', 'gt_bboxes_3d', 'gt_labels_3d'],
                    meta_keys=('filename', 'ori_shape', 'img_shape', 'lidar2img',
                               'depth2img', 'cam2img', 'pad_shape',
                               'scale_factor', 'flip', 'pcd_horizontal_flip',
                               'pcd_vertical_flip', 'box_mode_3d', 'box_type_3d',
                               'img_norm_cfg', 'pcd_trans', 'sample_idx',
                               'pcd_scale_factor', 'pcd_rotation', 'pts_filename',
                               'transformation_3d_flow', 'inf2veh', 
                               'infrastructure_pointcloud_bin_path_t_0', 'infrastructure_pointcloud_bin_path_t_1', 'infrastructure_pointcloud_bin_path_t_2',
                               'infrastructure_t_0_1', 'infrastructure_t_1_2')
                )
            ],
            modality=dict(use_lidar=True, use_camera=False),
            classes=class_names,
            test_mode=False,
            pcd_limit_range=point_cloud_range,
            box_type_3d='LiDAR')),
    val=dict(
        type=dataset_type,
        data_root=data_root,
        ann_file=data_info_val_path,
        split='training',
        pts_prefix='velodyne_reduced',
        pipeline=[
            dict(
                type='LoadPointsFromFile',
                coord_type='LIDAR',
                load_dim=4,
                use_dim=4,
                sensor_view='vehicle'),
            dict(
                type='LoadPointsFromFile',
                coord_type='LIDAR',
                load_dim=4,
                use_dim=4,
                sensor_view='infrastructure'),
            dict(
                type='MultiScaleFlipAug3D',
                img_scale=(h, l),
                pts_scale_ratio=1,
                flip=False,
                transforms=[
                    dict(
                        type='DefaultFormatBundle3D',
                        class_names=class_names,
                        with_label=False),
                    dict(type='Collect3D', keys=['points', 'infrastructure_points'],
                    meta_keys=('filename', 'ori_shape', 'img_shape', 'lidar2img',
                               'depth2img', 'cam2img', 'pad_shape',
                               'scale_factor', 'flip', 'pcd_horizontal_flip',
                               'pcd_vertical_flip', 'box_mode_3d', 'box_type_3d',
                               'img_norm_cfg', 'pcd_trans', 'sample_idx',
                               'pcd_scale_factor', 'pcd_rotation', 'pts_filename',
                               'transformation_3d_flow', 'inf2veh', 
                               'infrastructure_pointcloud_bin_path_t_0', 'infrastructure_pointcloud_bin_path_t_1', 'infrastructure_pointcloud_bin_path_t_2',
                               'infrastructure_t_0_1', 'infrastructure_t_1_2')
                        )
                ])
        ],
        modality=dict(use_lidar=True, use_camera=False),
        classes=class_names,
        test_mode=True,
        pcd_limit_range=point_cloud_range,
        box_type_3d='LiDAR'),
    test=dict(
        type=dataset_type,
        data_root=data_root,
        ann_file=data_info_val_path,
        split='training',
        pts_prefix='velodyne_reduced',
        pipeline=[
            dict(
                type='LoadPointsFromFile',
                coord_type='LIDAR',
                load_dim=4,
                use_dim=4,
                sensor_view='vehicle'),
            dict(
                type='LoadPointsFromFile',
                coord_type='LIDAR',
                load_dim=4,
                use_dim=4,
                sensor_view='infrastructure'),
            dict(
                type='MultiScaleFlipAug3D',
                img_scale=(h, l),
                pts_scale_ratio=1,
                flip=False,
                transforms=[
                    dict(
                        type='DefaultFormatBundle3D',
                        class_names=class_names,
                        with_label=False),
                    dict(type='Collect3D', keys=['points', 'infrastructure_points'],
                    meta_keys=('filename', 'ori_shape', 'img_shape', 'lidar2img',
                               'depth2img', 'cam2img', 'pad_shape',
                               'scale_factor', 'flip', 'pcd_horizontal_flip',
                               'pcd_vertical_flip', 'box_mode_3d', 'box_type_3d',
                               'img_norm_cfg', 'pcd_trans', 'sample_idx',
                               'pcd_scale_factor', 'pcd_rotation', 'pts_filename',
                               'transformation_3d_flow', 'inf2veh', 
                               'infrastructure_pointcloud_bin_path_t_0', 'infrastructure_pointcloud_bin_path_t_1', 'infrastructure_pointcloud_bin_path_t_2',
                               'infrastructure_t_0_1', 'infrastructure_t_1_2')
                        )
                ])
        ],
        modality=dict(use_lidar=True, use_camera=False),
        classes=class_names,
        test_mode=True,
        pcd_limit_range=point_cloud_range,
        box_type_3d='LiDAR'))
evaluation = dict(
    interval=2,
    pipeline=[
        dict(
            type='LoadPointsFromFile',
            coord_type='LIDAR',
            load_dim=4,
            use_dim=4,
            file_client_args=dict(backend='disk')),
        dict(
            type='DefaultFormatBundle3D',
            class_names=class_names,
            with_label=False),
        dict(type='Collect3D', keys=['points'])
    ])
lr = 0.001
optimizer = dict(type='AdamW', lr=0.001, betas=(0.95, 0.99), weight_decay=0.01)
optimizer_config = dict(grad_clip=dict(max_norm=35, norm_type=2))
lr_config = dict(
    policy='cyclic',
    target_ratio=(10, 0.0001),
    cyclic_times=1,
    step_ratio_up=0.4)
momentum_config = dict(
    policy='cyclic',
    target_ratio=(0.8947368421052632, 1),
    cyclic_times=1,
    step_ratio_up=0.4)
runner = dict(type='EpochBasedRunner', max_epochs=10)
checkpoint_config = dict(interval=10)
log_config = dict(
    interval=50,
    hooks=[dict(type='TextLoggerHook'),
           dict(type='TensorboardLoggerHook')])
dist_params = dict(backend='nccl')
log_level = 'INFO'
load_from = None
resume_from = None
workflow = [('train', 1)]
gpu_ids = range(0, 1)