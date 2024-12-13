from keras.src.api_export import keras_export
from keras.src.layers.preprocessing.image_preprocessing.base_image_preprocessing_layer import (  # noqa: E501
    BaseImagePreprocessingLayer,
)
from keras.src.random import SeedGenerator


@keras_export("keras.layers.MixUp")
class MixUp(BaseImagePreprocessingLayer):
    """MixUp implements the MixUp data augmentation technique.

    Args:
        alpha: Float between 0 and 1. Controls the blending strength.
               Smaller values mean less mixing, while larger values allow
               for more  blending between images. Defaults to 0.2,
               recommended for ImageNet1k classification.
        seed: Integer. Used to create a random seed.

    References:
        - [MixUp paper](https://arxiv.org/abs/1710.09412).
        - [MixUp for Object Detection paper](https://arxiv.org/pdf/1902.04103).

    Example:
    ```python
    (images, labels), _ = keras.datasets.cifar10.load_data()
    images, labels = images[:8], labels[:8]
    labels = keras.ops.cast(keras.ops.one_hot(labels.flatten(), 10), "float32")
    mix_up = keras.layers.MixUp(alpha=0.2)
    output = mix_up({"images": images, "labels": labels})
    ```
    """

    def __init__(self, alpha=0.2, data_format=None, seed=None, **kwargs):
        super().__init__(data_format=data_format, **kwargs)
        self.alpha = alpha
        self.seed = seed
        self.generator = SeedGenerator(seed)

    def get_random_transformation(self, data, training=True, seed=None):
        if isinstance(data, dict):
            images = data["images"]
        else:
            images = data

        images_shape = self.backend.shape(images)

        if len(images_shape) == 3:
            batch_size = 1
        else:
            batch_size = self.backend.shape(images)[0]

        if seed is None:
            seed = self._get_seed_generator(self.backend._backend)

        permutation_order = self.backend.random.shuffle(
            self.backend.numpy.arange(0, batch_size, dtype="int64"),
            seed=seed,
        )

        mix_weight = self.backend.random.beta(
            (batch_size,), self.alpha, self.alpha, seed=seed
        )
        return {
            "mix_weight": mix_weight,
            "permutation_order": permutation_order,
        }

    def transform_images(self, images, transformation=None, training=True):
        images = self.backend.cast(images, self.compute_dtype)
        mix_weight = transformation["mix_weight"]
        permutation_order = transformation["permutation_order"]

        mix_weight = self.backend.cast(
            self.backend.numpy.reshape(mix_weight, [-1, 1, 1, 1]),
            dtype=self.compute_dtype,
        )

        mix_up_images = self.backend.cast(
            self.backend.numpy.take(images, permutation_order, axis=0),
            dtype=self.compute_dtype,
        )

        images = mix_weight * images + (1.0 - mix_weight) * mix_up_images

        return images

    def transform_labels(self, labels, transformation, training=True):
        mix_weight = transformation["mix_weight"]
        permutation_order = transformation["permutation_order"]

        labels_for_mix_up = self.backend.numpy.take(
            labels, permutation_order, axis=0
        )

        mix_weight = self.backend.numpy.reshape(mix_weight, [-1, 1])

        labels = mix_weight * labels + (1.0 - mix_weight) * labels_for_mix_up

        return labels

    def transform_bounding_boxes(
        self,
        bounding_boxes,
        transformation,
        training=True,
    ):
        permutation_order = transformation["permutation_order"]
        boxes, classes = bounding_boxes["boxes"], bounding_boxes["classes"]
        boxes_for_mix_up = self.backend.numpy.take(boxes, permutation_order)
        classes_for_mix_up = self.backend.numpy.take(classes, permutation_order)
        boxes = self.backend.numpy.concat([boxes, boxes_for_mix_up], axis=1)
        classes = self.backend.numpy.concat(
            [classes, classes_for_mix_up], axis=1
        )
        return {"boxes": boxes, "classes": classes}

    def transform_segmentation_masks(
        self, segmentation_masks, transformation, training=True
    ):
        mix_weight = transformation["mix_weight"]
        permutation_order = transformation["permutation_order"]

        mix_weight = self.backend.numpy.reshape(mix_weight, [-1, 1, 1, 1])

        segmentation_masks_for_mix_up = self.backend.numpy.take(
            segmentation_masks, permutation_order
        )

        segmentation_masks = (
            mix_weight * segmentation_masks
            + (1.0 - mix_weight) * segmentation_masks_for_mix_up
        )

        return segmentation_masks

    def compute_output_shape(self, input_shape):
        return input_shape

    def get_config(self):
        config = {
            "alpha": self.alpha,
            "seed": self.seed,
        }
        base_config = super().get_config()
        return {**base_config, **config}
