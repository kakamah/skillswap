import argparse
import os
import shutil


DEFAULT_BASE_DIR = r"C:/Users/CoolPC/Desktop/Result"


FOLDER_MAP = {
    "Group 2 - Component A - Feature Engineering": [
        "Ali.md",
        "ALi1.md",
        "ALi2.md",
        "ALi3.md",
        "Ali4.md",
        "Ali5.md",
        "Ali6.md",
        "Ali7.md",
        "Ali8.md",
        "Ali9.md",
        "Ali10.md",
        "Ali11.md",
        "ALi12.md",
        "Ali13.md",
        "Ali14.md",
        "Ali15.md",
        "Ali16.md",
        "Ali17.md",
    ],
    "Group 3 - Component B - Solver Acceleration": [
        "Alinur.md",
        "Alinur1.md",
        "Alinur 2.md",
        "Alinur 3.md",
        "Alinur 4.md",
        "Alinur 5.md",
        "Alinur 6.md",
        "Alinur 7.md",
        "Alinur 8.md",
        "Alinur 9.md",
        "Alinur 10.md",
        "Alinur 11.md",
        "Alinur 12.md",
        "Alinur 13.md",
        "Alinur 14.md",
        "Alinur 14(1).md",
    ],
    os.path.join("Group 4 - Knowledge Base", "Subgroup 4.1 - Classical Models"): [
        "1 (1).md",
        "2.md",
        "3.md",
        "4.md",
        "5.md",
        "21TIP-SGNet.md",
        "Chen_Dynamic_Convolution_Attention_Over_Convolution_Kernels_CVPR_2020_paper.md",
        "Dai_Deformable_Convolutional_Networks_ICCV_2017_paper.md",
        "Esquivel_Adaptive_Convolutional_Kernels_ICCVW_2019_paper.md",
        "Klein_A_Dynamic_Convolutional_2015_CVPR_paper.md",
        "Metzger_Guided_Depth_Super-Resolution_by_Deep_Anisotropic_Diffusion_CVPR_2023_paper.md",
        "Park_Semantic_Image_Synthesis_With_Spatially-Adaptive_Normalization_CVPR_2019_paper.md",
        "Su_Pixel-Adaptive_Convolutional_Neural_Networks_CVPR_2019_paper.md",
        "Wang_Adaptive_Convolutions_With_Per-Pixel_Dynamic_Filter_Atom_ICCV_2021_paper.md",
        "Yamac_KernelNet_A_Blind_Super-Resolution_Kernel_Estimation_Network_CVPRW_2021_paper.md",
        "Zhou_Decoupled_Dynamic_Filter_Networks_CVPR_2021_paper.md",
        "1605.09673v2.md",
        "1712.02327v2.md",
        "1903.07291v2.md",
        "1903.11286v1.md",
        "1910.08313v2.md",
        "1910.08373v3.md",
        "2009.06385v1.md",
        "2108.07895v1.md",
        "2112.06401v2.md",
        "2401.04680v1.md",
        "2512.04556v1.md",
        "condconv-conditionally-parameterized-convolutions-for-30nfo8b7iv.md",
        "elsarticle_template20200621r2.md",
        "muller24a.md",
        "mutual-guided-dynamic-network-for-image-fusion-2ts4r2srct.md",
        "27907-Article Text-31961-1-2-20240324.md",
        "3550277-supp.md",
        "computers-12-00151.md",
        "sensors-24-07386.md",
        "sensors-24-07841.md",
        "Supplementary.md",
    ],
    os.path.join("Group 4 - Knowledge Base", "Subgroup 4.2 - PINNs and Solvers"): [
        "23-0064.md",
        "1710.09668v2.md",
        "1907.09032v3.md",
        "1910.03193v3.md",
        "2010.08895v3.md",
        "2011.10395v2.md",
        "2103.08834v2.md",
        "2511.16573v1.md",
    ],
    os.path.join("Group 4 - Knowledge Base", "Subgroup 4.3 - Quantum Computing"): [
        "0002077v3.md",
        "0201031v1.md",
        "0811.3171v3.md",
        "1208.0928v2.md",
        "1302.3428v7.md",
        "1302.5843v3.md",
        "1401.2910v1.md",
        "1411.4028v1.md",
        "1412.4687v1.md",
        "1605.03590v2.md",
        "1605.04570v1.md",
        "1704.05018v2.md",
        "1708.09757v2.md",
        "1801.00862v3.md",
        "1803.07128v1.md",
        "1803.11173v1.md",
        "1804.11326v2.md",
        "1807.04271v3.md",
        "1810.03787v2.md",
        "1810.10506v2.md",
        "1907.13022v2.md",
        "1910.11333v2.md",
        "1911.03446v1.md",
        "1912.08854v3.md",
        "2001.00550v3.md",
        "2011.01938v2.md",
        "2011.03185v3.md",
        "2012.01625v1.md",
        "2101.08448v2.md",
        "2102.01064v1.md",
        "2103.03074v1.md",
        "2207.06431v2.md",
        "2307.00523v1.md",
        "2312.14075v3.md",
        "2502.03790v1.md",
        "2503.12244v2.md",
        "2507.08554v1.md",
        "2508.09092v3.md",
        "2511.15969v1.md",
        "9605043v3.md",
        "9612003v1.md",
        "9702029v2.md",
        "9707021v1.md",
        "9804280v1.md",
        "bv.md",
        "feynman-quantum-1981.md",
        "Lloyd-1996.md",
        "NAE-report-on-quantum-computing.md",
        "shor.factoring.md",
        "MarincICIP19.md",
    ],
    os.path.join("Group 4 - Knowledge Base", "Subgroup 4.4 - Meteorology"): [
        "2002.00469v3.md",
        "2202.11214v1.md",
        "2212.12794v2.md",
        "2406.04099v2.md",
        "essd-13-4349-2021.md",
        "Quart J Royal Meteoro Soc - 2020 - Hersbach - The ERA5 global reanalysis.md",
        "s41586-024-08252-9.md",
    ],
}


def organize_files(base_dir: str) -> None:
    moved_files = []
    skipped_missing = []
    skipped_exists = []

    for relative_folder, file_list in FOLDER_MAP.items():
        destination_dir = os.path.join(base_dir, relative_folder)
        os.makedirs(destination_dir, exist_ok=True)

        for filename in file_list:
            source_path = os.path.join(base_dir, filename)
            destination_path = os.path.join(destination_dir, filename)

            if not os.path.isfile(source_path):
                skipped_missing.append(filename)
                continue

            if os.path.exists(destination_path):
                skipped_exists.append(filename)
                continue

            shutil.move(source_path, destination_path)
            moved_files.append((filename, relative_folder))

    print("\n=== Organization Summary ===")
    print(f"Base directory: {base_dir}")
    print(f"Moved files: {len(moved_files)}")
    print(f"Skipped (missing source): {len(skipped_missing)}")
    print(f"Skipped (destination already exists): {len(skipped_exists)}")

    if moved_files:
        print("\nMoved file details:")
        for filename, target_folder in moved_files:
            print(f"- {filename} -> {target_folder}")

    if skipped_missing:
        print("\nMissing files (not moved):")
        for filename in skipped_missing:
            print(f"- {filename}")

    if skipped_exists:
        print("\nFiles skipped because destination already exists:")
        for filename in skipped_exists:
            print(f"- {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize markdown files into project group folders."
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help=f'Root directory containing files to organize (default: "{DEFAULT_BASE_DIR}")',
    )
    args = parser.parse_args()
    organize_files(args.base_dir)


if __name__ == "__main__":
    main()
