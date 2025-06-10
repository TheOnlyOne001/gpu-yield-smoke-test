const sharp = require('sharp');
const fs = require('fs').promises;
const path = require('path');

async function optimizeImages() {
  const publicDir = path.join(process.cwd(), 'public');
  const imagesDir = path.join(publicDir, 'images');
  const outputDir = path.join(imagesDir, 'optimized');
  
  // Create output directory if it doesn't exist
  try {
    await fs.mkdir(outputDir, { recursive: true });
  } catch (err) {
    // Directory already exists
  }
  
  const files = await fs.readdir(imagesDir);
  
  for (const file of files) {
    if (file.match(/\.(jpg|jpeg|png)$/i)) {
      const inputPath = path.join(imagesDir, file);
      const webpPath = path.join(outputDir, file.replace(/\.(jpg|jpeg|png)$/i, '.webp'));
      const avifPath = path.join(outputDir, file.replace(/\.(jpg|jpeg|png)$/i, '.avif'));
      
      // Generate WebP
      await sharp(inputPath)
        .resize(2048, 2048, { 
          fit: 'inside',
          withoutEnlargement: true 
        })
        .webp({ quality: 85 })
        .toFile(webpPath);
        
      // Generate AVIF (even smaller than WebP)
      await sharp(inputPath)
        .resize(2048, 2048, { 
          fit: 'inside',
          withoutEnlargement: true 
        })
        .avif({ quality: 80 })
        .toFile(avifPath);
        
      console.log(`Optimized: ${file} -> WebP & AVIF`);
    }
  }
}

optimizeImages().catch(console.error);