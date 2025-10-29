"""Image optimization utility for agent-generated assets"""
import io
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageOps
import logging

logger = logging.getLogger(__name__)

# Image category specifications
IMAGE_SPECS = {
    "hero": {
        "max_res": (1920, 1080),
        "max_size_kb": 400,
        "format": "JPEG",  # progressive JPEG or WebP
        "prefer_webp": True
    },
    "section": {
        "max_res": (1200, 800),
        "max_size_kb": 250,
        "format": "WebP",  # preferred
        "fallback": "JPEG",
        "count": 4
    },
    "logo": {
        "max_res": (512, 512),
        "max_size_kb": 50,
        "format": "SVG",  # preferred
        "fallback": "PNG",
        "transparent_bg": True
    },
    "thumbnail": {
        "max_res": (800, 600),
        "max_size_kb": 150,
        "format": "WebP",
        "fallback": "JPEG",
        "max_count": 6,
        "total_max_kb": 1000
    }
}


class ImageOptimizer:
    """Optimizes images according to category specifications"""
    
    def __init__(self):
        self.total_size_bytes = 0
        self.max_total_size_bytes = 1.5 * 1024 * 1024  # 1.5 MB total limit
    
    async def download_image(self, url: str, timeout: int = 6) -> Optional[bytes]:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": "ImageOptimizerBot/1.0"}
            ) as session:
                async with session.get(url, allow_redirects=True, max_redirects=5) as response:
                    if 200 <= response.status < 300:
                        content_type = response.headers.get("Content-Type", "").lower()
                        if content_type.startswith("image/"):
                            data = await response.read()
                            if len(data) >= 4096:  # Min 4KB
                                return data
                            else:
                                logger.warning(f"Image too small: {url} ({len(data)} bytes)")
                    return None
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def _get_image_info(self, image_data: bytes) -> Optional[Tuple[Image.Image, int, int]]:
        """Get image dimensions"""
        try:
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            return img, width, height
        except Exception as e:
            logger.error(f"Error reading image: {e}")
            return None
    
    def _resize_with_aspect(self, img: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resize image maintaining aspect ratio, don't upscale"""
        original_width, original_height = img.size
        
        # Don't upscale
        if original_width <= max_width and original_height <= max_height:
            return img
        
        # Calculate new size maintaining aspect ratio
        ratio = min(max_width / original_width, max_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # Use high-quality resampling
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _optimize_image(
        self,
        image_data: bytes,
        category: str,
        filename: str
    ) -> Optional[Tuple[bytes, str, int, int]]:
        """
        Optimize image according to category spec
        Returns: (optimized_bytes, final_filename, width, height) or None
        """
        spec = IMAGE_SPECS.get(category, IMAGE_SPECS["thumbnail"])
        
        # Get image info
        img_info = self._get_image_info(image_data)
        if not img_info:
            return None
        
        img, original_width, original_height = img_info
        
        # Check if SVG (for logo category)
        if category == "logo" and filename.lower().endswith(".svg"):
            # For SVG, we can't optimize easily - just return as-is if size is OK
            if len(image_data) <= spec["max_size_kb"] * 1024:
                return (image_data, filename, original_width, original_height)
            logger.warning(f"SVG too large: {filename} ({len(image_data)} bytes)")
            return None
        
        # Resize if needed
        max_w, max_h = spec["max_res"]
        img = self._resize_with_aspect(img, max_w, max_h)
        width, height = img.size
        
        # Convert RGBA to RGB for JPEG if no transparency needed (except logo)
        output_format = spec.get("format", "WebP")
        if output_format in ("JPEG", "WebP") and category != "logo":
            if img.mode in ("RGBA", "LA", "P"):
                # Convert transparent to white background for JPEG
                if output_format == "JPEG" or not spec.get("transparent_bg", False):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img)
                    img = background
                elif output_format == "WebP" and img.mode == "RGBA":
                    # Keep transparency for WebP
                    pass
        
        # Optimize and convert
        output = io.BytesIO()
        optimize_kwargs = {}
        
        if output_format == "WebP" or spec.get("prefer_webp", False):
            # Try WebP first
            try:
                img.save(output, format="WebP", quality=85, method=6, optimize=True)
                optimized_data = output.getvalue()
                if len(optimized_data) <= spec["max_size_kb"] * 1024:
                    return (optimized_data, filename.rsplit(".", 1)[0] + ".webp", width, height)
            except Exception as e:
                logger.warning(f"WebP conversion failed: {e}, trying fallback")
            
            # Fallback to JPEG
            if spec.get("fallback") == "JPEG" or output_format == "JPEG":
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=85, optimize=True, progressive=True)
                optimized_data = output.getvalue()
                if len(optimized_data) <= spec["max_size_kb"] * 1024:
                    return (optimized_data, filename.rsplit(".", 1)[0] + ".jpg", width, height)
        
        elif output_format == "PNG":
            # PNG optimization (for logos)
            optimize_kwargs = {"optimize": True}
            if spec.get("transparent_bg", False):
                # Keep transparency
                img.save(output, format="PNG", **optimize_kwargs)
            else:
                # Convert to RGB
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img)
                    img = background
                img.save(output, format="PNG", **optimize_kwargs)
            
            optimized_data = output.getvalue()
            if len(optimized_data) <= spec["max_size_kb"] * 1024:
                return (optimized_data, filename.rsplit(".", 1)[0] + ".png", width, height)
        
        # If still too large, reduce quality further
        if len(output.getvalue()) > spec["max_size_kb"] * 1024:
            for quality in [75, 65, 55]:
                output = io.BytesIO()
                if output_format == "WebP" or spec.get("prefer_webp"):
                    img.save(output, format="WebP", quality=quality, method=6, optimize=True)
                else:
                    img.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
                
                if len(output.getvalue()) <= spec["max_size_kb"] * 1024:
                    ext = ".webp" if (output_format == "WebP" or spec.get("prefer_webp")) else ".jpg"
                    return (output.getvalue(), filename.rsplit(".", 1)[0] + ext, width, height)
        
        logger.warning(f"Could not optimize {filename} below {spec['max_size_kb']}KB")
        return None
    
    async def process_and_optimize_images(
        self,
        mapper_data: Dict[str, Any],
        workdir: Path
    ) -> Dict[str, Any]:
        """
        Download, optimize, and store images from mapper_data
        
        Returns:
            Dict with optimized image metadata for use in HTML generation
        """
        assets_dir = workdir / "assets" / "images"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        optimized_images = []
        self.total_size_bytes = 0
        
        # Get logo (if present)
        logo_url = mapper_data.get("assats", {}).get("logo_url")
        if logo_url:
            logger.info(f"[ImageOptimizer] Processing logo: {logo_url}")
            img_data = await self.download_image(logo_url)
            if img_data:
                result = self._optimize_image(img_data, "logo", "logo")
                if result:
                    optimized_bytes, filename, width, height = result
                    
                    # Check total size limit
                    if self.total_size_bytes + len(optimized_bytes) > self.max_total_size_bytes:
                        logger.warning("Total bundle size limit reached, skipping logo")
                    else:
                        # Save image
                        logo_path = assets_dir / filename
                        logo_path.write_bytes(optimized_bytes)
                        self.total_size_bytes += len(optimized_bytes)
                        
                        optimized_images.append({
                            "type": "logo",
                            "filename": filename,
                            "path": f"assets/images/{filename}",
                            "width": width,
                            "height": height,
                            "size_kb": len(optimized_bytes) / 1024
                        })
                        logger.info(f"[ImageOptimizer] Saved logo: {filename} ({len(optimized_bytes)/1024:.1f}KB, {width}x{height})")
        
        # Get business images (categorize as section/feature images)
        business_images = mapper_data.get("assats", {}).get("business_images_urls", [])
        if business_images:
            # Limit to 4 section images - download in parallel for speed
            business_tasks = []
            for i, url in enumerate(business_images[:4]):
                logger.info(f"[ImageOptimizer] Queueing business image {i+1}: {url}")
                business_tasks.append((i, url, self.download_image(url)))
            
            # Download all in parallel with timeout per image (each has 6s timeout)
            business_results = await asyncio.gather(*[task[2] for task in business_tasks], return_exceptions=True)
            
            for (i, url, _), img_data in zip(business_tasks, business_results):
                if isinstance(img_data, Exception):
                    logger.error(f"[ImageOptimizer] Failed to download business image {i+1}: {img_data}")
                    continue
                if not img_data:
                    logger.warning(f"[ImageOptimizer] No image data returned for business image {i+1}: {url}")
                    continue
                result = self._optimize_image(img_data, "section", f"business_{i}")
                if result:
                    optimized_bytes, filename, width, height = result
                    
                    if self.total_size_bytes + len(optimized_bytes) > self.max_total_size_bytes:
                        logger.warning("Total bundle size limit reached, stopping image processing")
                        break
                    
                    # Save image
                    img_path = assets_dir / filename
                    img_path.write_bytes(optimized_bytes)
                    self.total_size_bytes += len(optimized_bytes)
                    
                    optimized_images.append({
                        "type": "section",
                        "filename": filename,
                        "path": f"assets/images/{filename}",
                        "width": width,
                        "height": height,
                        "size_kb": len(optimized_bytes) / 1024
                    })
                    logger.info(f"[ImageOptimizer] Saved business image: {filename} ({len(optimized_bytes)/1024:.1f}KB, {width}x{height})")
        
        # Get stock images (categorize as thumbnails/gallery)
        stock_images = mapper_data.get("assats", {}).get("stock_images_urls", [])
        if stock_images:
            # Limit to 6 thumbnails - download in parallel for speed
            stock_tasks = []
            for i, url in enumerate(stock_images[:6]):
                logger.info(f"[ImageOptimizer] Queueing stock image {i+1}: {url}")
                stock_tasks.append((i, url, self.download_image(url)))
            
            # Download all in parallel with timeout per image
            stock_results = await asyncio.gather(*[task[2] for task in stock_tasks], return_exceptions=True)
            
            for (i, url, _), img_data in zip(stock_tasks, stock_results):
                if isinstance(img_data, Exception):
                    logger.error(f"[ImageOptimizer] Failed to download stock image {i+1}: {img_data}")
                    continue
                if not img_data:
                    logger.warning(f"[ImageOptimizer] No image data returned for stock image {i+1}: {url}")
                    continue
                result = self._optimize_image(img_data, "thumbnail", f"stock_{i}")
                if result:
                    optimized_bytes, filename, width, height = result
                    
                    thumbnail_total = sum(
                        img.get("size_kb", 0) * 1024 
                        for img in optimized_images 
                        if img.get("type") == "thumbnail"
                    )
                    if thumbnail_total + len(optimized_bytes) > IMAGE_SPECS["thumbnail"]["total_max_kb"] * 1024:
                        logger.warning("Thumbnail gallery size limit reached")
                        break
                    
                    if self.total_size_bytes + len(optimized_bytes) > self.max_total_size_bytes:
                        logger.warning("Total bundle size limit reached, stopping image processing")
                        break
                    
                    # Save image
                    img_path = assets_dir / filename
                    img_path.write_bytes(optimized_bytes)
                    self.total_size_bytes += len(optimized_bytes)
                    
                    optimized_images.append({
                        "type": "thumbnail",
                        "filename": filename,
                        "path": f"assets/images/{filename}",
                        "width": width,
                        "height": height,
                        "size_kb": len(optimized_bytes) / 1024
                    })
                    logger.info(f"[ImageOptimizer] Saved stock image: {filename} ({len(optimized_bytes)/1024:.1f}KB, {width}x{height})")
        
        # Identify hero image (first section image, optimized to hero spec if needed)
        hero_image = None
        for img in optimized_images:
            if img["type"] == "section":
                # If section image is too large for hero spec, create hero version
                if img["width"] > 1920 or img["height"] > 1080 or img.get("size_kb", 0) > 400:
                    # Read the original optimized file and re-optimize for hero
                    img_path = assets_dir / img["filename"]
                    if img_path.exists():
                        hero_data = img_path.read_bytes()
                        hero_result = self._optimize_image(hero_data, "hero", f"hero_{img['filename']}")
                        if hero_result:
                            optimized_bytes, filename, width, height = hero_result
                            hero_path = assets_dir / filename
                            hero_path.write_bytes(optimized_bytes)
                            hero_image = {
                                "type": "hero",
                                "filename": filename,
                                "path": f"assets/images/{filename}",
                                "width": width,
                                "height": height,
                                "size_kb": len(optimized_bytes) / 1024
                            }
                else:
                    # Use section image as hero as-is
                    hero_image = {**img, "type": "hero"}
                break
        
        logger.info(f"[ImageOptimizer] Total images processed: {len(optimized_images)}, Total size: {self.total_size_bytes/1024:.1f}KB")
        
        return {
            "images": optimized_images,
            "hero_image": hero_image,
            "total_size_kb": self.total_size_bytes / 1024,
            "logo": next((img for img in optimized_images if img["type"] == "logo"), None)
        }


# Global optimizer instance
image_optimizer = ImageOptimizer()
