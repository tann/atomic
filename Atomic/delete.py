from . import Atomic
from . import util
import sys
from Atomic.backendutils import BackendUtils

class Delete(Atomic):
    def __init__(self):
        super(Delete, self).__init__()

    def delete_image(self):
        """
        Mark given image(s) for deletion from registry
        :return: 0 if all images marked for deletion, otherwise 2 on any failure
        """
        if self.args.debug:
            util.write_out(str(self.args))

        beu = BackendUtils()
        # Ensure the input values match up first
        delete_objects = []

        # We need to decide on new returns for dbus because we now check image
        # validity prior to executing the delete.  If there is going to be a
        # failure, it will be here.
        #
        # The failure here is basically that it couldnt verify/find the image.

        for image in self.args.delete_targets:
            be, img_obj = beu.get_backend_and_image(image, str_preferred_backend=self.args.storage)
            delete_objects.append((be, img_obj))

        if self.args.remote:
            return self._delete_remote(self.args.delete_targets)

        max_img_name = max([len(x.input_name) for _, x in delete_objects]) + 2

        if not self.args.assumeyes:
            util.write_out("Do you wish to delete the following images?\n")
            two_col = "   {0:" + str(max_img_name) + "} {1}"
            util.write_out(two_col.format("IMAGE", "STORAGE"))
            for del_obj in delete_objects:
                be, img_obj = del_obj
                util.write_out(two_col.format(img_obj.input_name, be.backend))
            confirm = util.input("\nConfirm (y/N) ")
            confirm = confirm.strip().lower()
            if not confirm in ['y', 'yes']:
                util.write_err("User aborted delete operation for {}".format(self.args.delete_targets))
                sys.exit(2)

        # Perform the delete
        for del_obj in delete_objects:
            be, img_obj = del_obj
            be.delete_image(img_obj.input_name, force=self.args.force)

        # We need to return something here for dbus
        return

    def prune_images(self):
        """
        Remove dangling images from registry
        :return: 0 if all images deleted or no dangling images found
        """

        if self.args.debug:
            util.write_out(str(self.args))

        for backend in BackendUtils.BACKENDS:
            be = backend()
            be.prune()

        return 0

    def _delete_remote(self, targets):
        results = 0
        for target in targets:
            # _convert_to_skopeo requires registry v1 support while delete requires v2 support
            # args, img = self.syscontainers._convert_to_skopeo(target)

            args = []
            if "http:" in target:
                args.append("--insecure")

            for i in ["oci:", "http:", "https:"]:
                img = target.replace(i, "docker:")

            if not img.startswith("docker:"):
                img = "docker://" + img

            try:
                util.skopeo_delete(img, args)
                util.write_out("Image {} marked for deletion".format(img))
            except ValueError as e:
                util.write_err("Failed to mark Image {} for deletion: {}".format(img, e))
                results = 2
        return results


