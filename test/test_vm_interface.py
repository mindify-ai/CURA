from vm import VM_with_interface

image_name = "swe_img:latest"

def test_vm_init():
    with VM_with_interface(image_name=image_name) as vm:
        assert vm._image_name == image_name
        assert vm.interface is not None
        assert vm.run_command(f"cat {vm.container_interface_path}") == open(vm.host_interface_path).read()