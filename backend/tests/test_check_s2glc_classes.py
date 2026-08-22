import rasterio
import numpy as np
import sys
import time

def get_unique_values(filepath):
    unique_vals = set()
    print(f"Obrint {filepath}...")
    with rasterio.open(filepath) as src:
        windows = [window for ij, window in src.block_windows(1)]
        total_blocks = len(windows)
        print(f"L'arxiu té {total_blocks} blocs. Començant la lectura...")
        
        start_time = time.time()
        for i, window in enumerate(windows):
            data = src.read(1, window=window)
            unique_vals.update(np.unique(data))
            
            # Imprimir progrés cada 1000 blocs
            if i % 10000 == 0 and i > 0:
                elapsed = time.time() - start_time
                print(f"Processat {i}/{total_blocks} blocs ({(i/total_blocks)*100:.1f}%) en {elapsed:.1f}s. Únics trobats fins ara: {sorted(list(unique_vals))}")
                
    return sorted(list(unique_vals))

if __name__ == '__main__':
    path = r'I:\TerraLab\data\earth\surface\Cobertura_del_s_l_categ_rica\S2GLC_Europe_2017_v1.2.tif'
    try:
        vals = get_unique_values(path)
        print("\n" + "="*50)
        print("RESULTAT FINAL - Valors únics al raster:")
        print(vals)
        print("="*50)
    except Exception as e:
        print(f"Error: {e}")
