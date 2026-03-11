"""Seed demo data into CRUD PostgreSQL tables.

This script is intended for demonstration environments and runs inside AKS,
using the same PostgreSQL environment variables configured for the CRUD service.

Uses curated retail product catalog data instead of random Faker output to
provide a realistic storefront experience for demos and development.
"""

import asyncio
import json
import os
import random
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
from azure.identity.aio import DefaultAzureCredential

# ---------------------------------------------------------------------------
# Curated retail catalog data
# ---------------------------------------------------------------------------

CATEGORIES: list[dict] = [
    {
        "id": "cat-electronics",
        "name": "Electronics",
        "slug": "electronics",
        "description": "Smartphones, laptops, tablets, and accessories for the modern holiday shopper.",
        "image_url": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&q=80",
    },
    {
        "id": "cat-clothing",
        "name": "Clothing & Apparel",
        "slug": "clothing-apparel",
        "description": "Seasonal fashion, outerwear, and holiday party attire for the whole family.",
        "image_url": "https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&q=80",
    },
    {
        "id": "cat-home-kitchen",
        "name": "Home & Kitchen",
        "slug": "home-kitchen",
        "description": "Cookware, small appliances, and home décor to make the holidays special.",
        "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=80",
    },
    {
        "id": "cat-toys-games",
        "name": "Toys & Games",
        "slug": "toys-games",
        "description": "Top-rated toys, board games, and puzzles for kids of all ages.",
        "image_url": "https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=800&q=80",
    },
    {
        "id": "cat-sports-outdoors",
        "name": "Sports & Outdoors",
        "slug": "sports-outdoors",
        "description": "Fitness gear, outdoor equipment, and winter sports essentials.",
        "image_url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=800&q=80",
    },
    {
        "id": "cat-beauty-health",
        "name": "Beauty & Health",
        "slug": "beauty-health",
        "description": "Skincare sets, wellness products, and premium gift sets.",
        "image_url": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=80",
    },
    {
        "id": "cat-books-media",
        "name": "Books & Media",
        "slug": "books-media",
        "description": "Bestselling books, vinyl records, and streaming gift cards.",
        "image_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=800&q=80",
    },
    {
        "id": "cat-jewelry-watches",
        "name": "Jewelry & Watches",
        "slug": "jewelry-watches",
        "description": "Fine jewelry, fashion watches, and luxury accessories.",
        "image_url": "https://images.unsplash.com/photo-1515562141589-67f0d569b6c4?w=800&q=80",
    },
    {
        "id": "cat-food-gourmet",
        "name": "Food & Gourmet",
        "slug": "food-gourmet",
        "description": "Artisan chocolates, holiday gift baskets, and gourmet selections.",
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",
    },
    {
        "id": "cat-pet-supplies",
        "name": "Pet Supplies",
        "slug": "pet-supplies",
        "description": "Premium pet food, cozy beds, toys, and holiday treats for furry friends.",
        "image_url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=800&q=80",
    },
]

# Each entry: (name, description, price, features, image_keyword)
_PRODUCTS_BY_CATEGORY: dict[str, list[tuple[str, str, float, list[str], str]]] = {
    "cat-electronics": [
        (
            "Wireless Noise-Cancelling Headphones",
            "Premium over-ear headphones with active noise cancellation, 30-hour battery life, and Hi-Res audio support.",
            249.99,
            ["Noise Cancelling", "Bluetooth 5.3", "30h Battery"],
            "headphones",
        ),
        (
            'Ultra-Slim 15" Laptop',
            'Lightweight laptop with 15.6" OLED display, 16 GB RAM, 512 GB SSD, and all-day battery.',
            899.99,
            ["OLED Display", "16 GB RAM", "512 GB SSD"],
            "laptop",
        ),
        (
            "Smart 4K Streaming Stick",
            "Plug-and-play 4K HDR streaming device with voice remote and Dolby Atmos support.",
            39.99,
            ["4K HDR", "Voice Control", "Dolby Atmos"],
            "streaming-device",
        ),
        (
            "Portable Bluetooth Speaker",
            "Waterproof portable speaker with 360° sound, 12-hour playtime, and built-in microphone.",
            79.99,
            ["Waterproof IP67", "12h Playtime", "360° Sound"],
            "bluetooth-speaker",
        ),
        (
            "Wireless Charging Pad Duo",
            "Dual wireless charger for phone and earbuds with Qi2 fast charging up to 15 W.",
            34.99,
            ["Qi2 Fast Charge", "Dual Device", "LED Indicator"],
            "wireless-charger",
        ),
        (
            "Smart Fitness Tracker",
            "Advanced fitness band with heart rate monitoring, GPS, sleep tracking, and 7-day battery.",
            129.99,
            ["Heart Rate", "Built-in GPS", "7-Day Battery"],
            "fitness-tracker",
        ),
        (
            "Mechanical Gaming Keyboard",
            "RGB mechanical keyboard with hot-swappable switches, N-key rollover, and aluminum frame.",
            119.99,
            ["Hot-Swap Switches", "RGB Backlit", "N-Key Rollover"],
            "gaming-keyboard",
        ),
        (
            "USB-C Hub 8-in-1",
            "Multiport adapter with HDMI 4K, USB-A, SD card reader, Ethernet, and 100 W pass-through charging.",
            49.99,
            ["HDMI 4K", "100 W PD", "8 Ports"],
            "usb-hub",
        ),
        (
            "True Wireless Earbuds Pro",
            "In-ear wireless earbuds with adaptive ANC, transparency mode, and wireless charging case.",
            179.99,
            ["Adaptive ANC", "Wireless Case", "IPX4"],
            "wireless-earbuds",
        ),
        (
            "Digital Drawing Tablet",
            '10" pen display with 8192 pressure levels, tilt support, and laminated screen.',
            199.99,
            ["8192 Pressure Levels", "Tilt Support", '10" Display'],
            "drawing-tablet",
        ),
    ],
    "cat-clothing": [
        (
            "Merino Wool Crewneck Sweater",
            "Classic-fit crewneck sweater in 100% extra-fine Merino wool. Machine washable.",
            89.99,
            ["Merino Wool", "Machine Washable", "Classic Fit"],
            "sweater",
        ),
        (
            "Insulated Puffer Jacket",
            "Lightweight and warm puffer jacket with recycled fill, water-resistant shell, and packable design.",
            149.99,
            ["Recycled Fill", "Water Resistant", "Packable"],
            "puffer-jacket",
        ),
        (
            "Stretch Slim Chinos",
            "Comfortable slim-fit chinos with 2% stretch for all-day comfort. Available in 6 colors.",
            59.99,
            ["2% Stretch", "Slim Fit", "6 Colors"],
            "chinos",
        ),
        (
            "Holiday Flannel Pajama Set",
            "Cozy brushed cotton flannel pajama set with festive plaid pattern.",
            44.99,
            ["Brushed Cotton", "Button Front", "Plaid Pattern"],
            "flannel-pajamas",
        ),
        (
            "Cashmere Blend Scarf",
            "Luxuriously soft cashmere-blend scarf in timeless herringbone pattern.",
            65.00,
            ["Cashmere Blend", "Herringbone", "Unisex"],
            "scarf",
        ),
        (
            "Sherpa-Lined Hoodie",
            "Heavyweight hoodie with plush sherpa lining, kangaroo pocket, and ribbed cuffs.",
            74.99,
            ["Sherpa Lined", "Heavyweight", "Kangaroo Pocket"],
            "hoodie",
        ),
        (
            "Performance Running Tights",
            "High-waist running tights with side pockets, reflective details, and moisture-wicking fabric.",
            68.00,
            ["Moisture Wicking", "Reflective", "Side Pockets"],
            "running-tights",
        ),
        (
            "Leather Chelsea Boots",
            "Handcrafted leather Chelsea boots with cushioned insole and durable rubber outsole.",
            189.99,
            ["Genuine Leather", "Cushioned Insole", "Rubber Sole"],
            "chelsea-boots",
        ),
        (
            "Down-Fill Vest",
            "Lightweight goose-down vest with snap pockets and elasticized armholes.",
            99.99,
            ["Goose Down", "Snap Pockets", "Lightweight"],
            "down-vest",
        ),
        (
            "Silk Tie Gift Set",
            "Set of three premium silk ties in a presentation gift box.",
            79.99,
            ["100% Silk", "Gift Box", "3-Pack"],
            "silk-ties",
        ),
    ],
    "cat-home-kitchen": [
        (
            "Cast Iron Dutch Oven 6 Qt",
            "Enameled cast iron Dutch oven with self-basting lid. Oven safe to 500°F.",
            89.99,
            ["Enameled Cast Iron", "6 Quart", "Oven Safe 500°F"],
            "dutch-oven",
        ),
        (
            "Smart Coffee Maker",
            "12-cup programmable coffee maker with WiFi, brew scheduling, and thermal carafe.",
            129.99,
            ["WiFi Connected", "Thermal Carafe", "12-Cup"],
            "coffee-maker",
        ),
        (
            "Scented Candle Gift Set",
            "Set of four hand-poured soy candles in seasonal fragrances: Pine, Cinnamon, Vanilla, and Cranberry.",
            42.99,
            ["Soy Wax", "4-Pack", "40h Burn Time"],
            "candle-set",
        ),
        (
            "Cotton Waffle Throw Blanket",
            'Oversized waffle-knit throw in organic cotton. 60" × 80".',
            54.99,
            ["Organic Cotton", '60×80"', "Waffle Knit"],
            "throw-blanket",
        ),
        (
            "Air Fryer 5.8 Qt",
            "Digital air fryer with 8 presets, non-stick basket, and rapid air circulation.",
            79.99,
            ["5.8 Quart", "8 Presets", "Non-Stick"],
            "air-fryer",
        ),
        (
            "Bamboo Cutting Board Set",
            "Three-piece bamboo cutting board set with juice grooves and easy-grip handles.",
            29.99,
            ["Bamboo", "3-Piece Set", "Juice Grooves"],
            "cutting-boards",
        ),
        (
            "Stand Mixer 5 Qt",
            "Tilt-head stand mixer with 10 speeds, stainless steel bowl, and three attachments.",
            299.99,
            ["10 Speeds", "5 Quart", "3 Attachments"],
            "stand-mixer",
        ),
        (
            "Ceramic Dinnerware Set 16-Piece",
            "Modern stoneware dinnerware set for 4. Microwave and dishwasher safe.",
            69.99,
            ["Stoneware", "16-Piece", "Dishwasher Safe"],
            "dinnerware",
        ),
        (
            "Smart LED Light Strip 16 ft",
            "WiFi-enabled RGB LED strip with music sync, voice control, and app scheduling.",
            24.99,
            ["16 ft", "Music Sync", "Voice Control"],
            "led-strip",
        ),
        (
            "Essential Oil Diffuser",
            "Ultrasonic aromatherapy diffuser with 7 LED colors and 300 ml tank.",
            34.99,
            ["Ultrasonic", "300 ml", "7 LED Colors"],
            "diffuser",
        ),
    ],
    "cat-toys-games": [
        (
            "Building Block Castle Set",
            "1,200-piece medieval castle building set with 8 minifigures and working drawbridge.",
            69.99,
            ["1200 Pieces", "8 Minifigures", "Ages 8+"],
            "building-blocks",
        ),
        (
            "Remote Control Monster Truck",
            "1:16 scale RC monster truck with 4WD, 2.4 GHz remote, and rechargeable battery.",
            44.99,
            ["1:16 Scale", "4WD", "2.4 GHz"],
            "rc-truck",
        ),
        (
            "Strategy Board Game Collection",
            "Family game night bundle with three award-winning strategy board games.",
            54.99,
            ["3 Games", "2-6 Players", "Ages 10+"],
            "board-games",
        ),
        (
            "Interactive Coding Robot",
            "Programmable robot toy that teaches coding through play. Compatible with block-based coding app.",
            79.99,
            ["App Compatible", "STEM Learning", "Ages 6+"],
            "coding-robot",
        ),
        (
            "1000-Piece Jigsaw Puzzle",
            "Holiday winter landscape 1000-piece jigsaw puzzle with poster guide.",
            19.99,
            ["1000 Pieces", "Poster Guide", "Winter Theme"],
            "jigsaw-puzzle",
        ),
        (
            "Wooden Train Set 100-Piece",
            "Classic wooden railway set with tracks, bridges, trains, and town accessories.",
            49.99,
            ["100 Pieces", "Real Wood", "Ages 3+"],
            "train-set",
        ),
        (
            "Art Supply Kit Deluxe",
            "150-piece art kit with colored pencils, markers, watercolors, and carry case.",
            34.99,
            ["150 Pieces", "Carry Case", "All Media"],
            "art-kit",
        ),
        (
            "Outdoor Adventure Binoculars",
            "Kid-friendly 8×21 binoculars with rubber grip, neck strap, and carry pouch.",
            24.99,
            ["8×21 Zoom", "Rubber Grip", "Carry Pouch"],
            "kids-binoculars",
        ),
        (
            "Plush Stuffed Animal Collection",
            'Set of three ultra-soft plush animals: bear, bunny, and fox. 12" each.',
            29.99,
            ["3-Pack", "Ultra Soft", '12" Each'],
            "plush-animals",
        ),
        (
            "Science Experiment Kit",
            "Over 30 science experiments covering chemistry, physics, and biology for young scientists.",
            39.99,
            ["30+ Experiments", "Lab Manual", "Ages 8+"],
            "science-kit",
        ),
    ],
    "cat-sports-outdoors": [
        (
            "Insulated Stainless Steel Water Bottle",
            "32 oz vacuum-insulated bottle that keeps drinks cold 24 h or hot 12 h.",
            29.99,
            ["32 oz", "Vacuum Insulated", "BPA Free"],
            "water-bottle",
        ),
        (
            "Yoga Mat Premium 6 mm",
            "Non-slip TPE yoga mat with alignment lines and carrying strap.",
            39.99,
            ["6 mm Thick", "Non-Slip TPE", "Alignment Lines"],
            "yoga-mat",
        ),
        (
            "Adjustable Dumbbell Set",
            "Pair of adjustable dumbbells from 5 to 25 lb each with quick-lock mechanism.",
            199.99,
            ["5-25 lb", "Quick-Lock", "Pair"],
            "dumbbells",
        ),
        (
            "Winter Ski Goggles",
            "Anti-fog dual-lens ski goggles with UV400 protection and OTG design for glasses.",
            59.99,
            ["Anti-Fog", "UV400", "OTG Compatible"],
            "ski-goggles",
        ),
        (
            "Camping Hammock with Straps",
            "Lightweight parachute nylon hammock supporting up to 400 lb, with tree straps included.",
            32.99,
            ["Parachute Nylon", "400 lb Capacity", "Tree Straps"],
            "hammock",
        ),
        (
            "Resistance Band Set",
            "Five-level resistance band set with door anchor, handles, and ankle straps.",
            24.99,
            ["5 Bands", "Door Anchor", "Handles Included"],
            "resistance-bands",
        ),
        (
            "Trail Running Shoes",
            "Breathable trail runners with Vibram outsole, rock plate, and waterproof membrane.",
            134.99,
            ["Vibram Outsole", "Waterproof", "Rock Plate"],
            "trail-shoes",
        ),
        (
            "Compression Recovery Boots",
            "Pneumatic leg compression system with 4 chambers and adjustable intensity.",
            249.99,
            ["4 Chambers", "Adjustable Intensity", "Travel Bag"],
            "recovery-boots",
        ),
        (
            "Folding Camping Chair",
            "Compact folding chair with cup holder, side pocket, and 300 lb capacity.",
            34.99,
            ["300 lb Capacity", "Cup Holder", "Carry Bag"],
            "camping-chair",
        ),
        (
            "GPS Running Watch",
            "Multisport GPS watch with wrist HR, pace coaching, and 14-day battery life.",
            299.99,
            ["GPS + HR", "Pace Coach", "14-Day Battery"],
            "running-watch",
        ),
    ],
    "cat-beauty-health": [
        (
            "Vitamin C Brightening Serum",
            "30 ml facial serum with 20% Vitamin C, hyaluronic acid, and ferulic acid.",
            28.99,
            ["20% Vitamin C", "Hyaluronic Acid", "30 ml"],
            "vitamin-c-serum",
        ),
        (
            "Electric Toothbrush Pro",
            "Sonic electric toothbrush with 5 modes, pressure sensor, and 2-week battery.",
            69.99,
            ["Sonic", "5 Modes", "Pressure Sensor"],
            "electric-toothbrush",
        ),
        (
            "Luxury Bath Bomb Set",
            "Set of 12 handcrafted bath bombs with essential oils and shea butter.",
            24.99,
            ["12-Pack", "Essential Oils", "Shea Butter"],
            "bath-bombs",
        ),
        (
            "Hair Dryer Professional",
            "1875 W ionic hair dryer with diffuser, concentrator, and cool-shot button.",
            49.99,
            ["1875 W", "Ionic", "3 Attachments"],
            "hair-dryer",
        ),
        (
            "Retinol Night Cream",
            "50 ml anti-aging night cream with encapsulated retinol and peptide complex.",
            38.99,
            ["Retinol", "Peptide Complex", "50 ml"],
            "night-cream",
        ),
        (
            "Aromatherapy Gift Set",
            "Collection of 6 pure essential oils: lavender, eucalyptus, peppermint, tea tree, lemon, and orange.",
            22.99,
            ["6 Oils", "100% Pure", "Gift Box"],
            "essential-oils",
        ),
        (
            "Jade Facial Roller Set",
            "Dual-ended jade roller and gua sha set in bamboo packaging.",
            19.99,
            ["Natural Jade", "Dual-Ended", "Gua Sha Included"],
            "jade-roller",
        ),
        (
            "Men's Grooming Kit",
            "Complete grooming set with trimmer, scissors, comb, and leather travel case.",
            44.99,
            ["6-Piece", "Stainless Steel", "Travel Case"],
            "grooming-kit",
        ),
        (
            "SPF 50 Daily Sunscreen",
            "Lightweight daily sunscreen with broad-spectrum SPF 50 and no white cast.",
            16.99,
            ["SPF 50", "Broad Spectrum", "Lightweight"],
            "sunscreen",
        ),
        (
            "Heated Eye Mask",
            "USB-rechargeable heated eye mask with lavender inserts for relaxation.",
            29.99,
            ["Heated", "Lavender Inserts", "Rechargeable"],
            "eye-mask",
        ),
    ],
    "cat-books-media": [
        (
            "Bestseller Fiction Box Set",
            "Collection of three New York Times bestselling novels in hardcover.",
            39.99,
            ["3 Books", "Hardcover", "NYT Bestseller"],
            "book-set",
        ),
        (
            "Vinyl Record Player",
            "Belt-drive turntable with built-in speakers, Bluetooth output, and USB recording.",
            129.99,
            ["Belt-Drive", "Bluetooth", "USB Recording"],
            "record-player",
        ),
        (
            "Cookbook: Holiday Feasts",
            "200+ holiday recipes from around the world with full-color photography.",
            29.99,
            ["200+ Recipes", "Full Color", "Hardcover"],
            "cookbook",
        ),
        (
            "Streaming Gift Card $50",
            "Digital gift card redeemable on major streaming platforms.",
            50.00,
            ["$50 Value", "Digital Delivery", "Multi-Platform"],
            "gift-card-streaming",
        ),
        (
            "Podcasting Microphone Kit",
            "USB condenser microphone with pop filter, boom arm, and shock mount.",
            89.99,
            ["USB-C", "Pop Filter", "Boom Arm"],
            "podcast-mic",
        ),
        (
            "Adult Coloring Book Set",
            "Set of three premium coloring books with 120 intricate designs and 24 colored pencils.",
            24.99,
            ["3 Books", "120 Designs", "Pencils Included"],
            "coloring-books",
        ),
        (
            "E-Reader Paperwhite",
            '6.8" glare-free display e-reader with adjustable warm light and 16 GB storage.',
            139.99,
            ['6.8" Display', "Warm Light", "16 GB"],
            "e-reader",
        ),
        (
            "Music Theory for Beginners",
            "Comprehensive guide to music theory with exercises and online video lessons.",
            19.99,
            ["Beginner Friendly", "Online Videos", "Paperback"],
            "music-theory",
        ),
        (
            "Audiobook Subscription Gift",
            "3-month audiobook subscription with one credit per month.",
            44.97,
            ["3 Months", "1 Credit/Month", "Gift Card"],
            "audiobook-sub",
        ),
        (
            "Photography Art Book",
            "Large-format coffee table book showcasing award-winning landscape photography.",
            49.99,
            ["Large Format", "200 Photos", "Hardcover"],
            "photo-book",
        ),
    ],
    "cat-jewelry-watches": [
        (
            "Sterling Silver Pendant Necklace",
            'Handcrafted sterling silver pendant on 18" chain with spring-ring clasp.',
            59.99,
            ["925 Sterling Silver", '18" Chain', "Handcrafted"],
            "pendant-necklace",
        ),
        (
            "Automatic Dive Watch",
            "200 m water-resistant automatic watch with sapphire crystal and stainless steel bracelet.",
            349.99,
            ["Automatic", "Sapphire Crystal", "200 m WR"],
            "dive-watch",
        ),
        (
            "Gold-Plated Hoop Earrings",
            "18K gold-plated stainless steel hoop earrings. Hypoallergenic and tarnish resistant.",
            29.99,
            ["18K Gold Plated", "Hypoallergenic", "Stainless Steel"],
            "hoop-earrings",
        ),
        (
            "Minimalist Leather Watch",
            "Ultra-thin quartz watch with genuine leather strap and Japanese movement.",
            89.99,
            ["Japanese Quartz", "Leather Strap", "Ultra-Thin"],
            "leather-watch",
        ),
        (
            "Freshwater Pearl Bracelet",
            "Elegant bracelet featuring genuine freshwater pearls on sterling silver wire.",
            45.00,
            ["Freshwater Pearls", "Sterling Silver", "Adjustable"],
            "pearl-bracelet",
        ),
        (
            "Chronograph Sport Watch",
            "Stainless steel chronograph with tachymeter bezel and 100 m water resistance.",
            179.99,
            ["Chronograph", "Tachymeter", "100 m WR"],
            "sport-watch",
        ),
        (
            "Birthstone Ring Collection",
            "Stackable birthstone ring in your choice of 12 gemstones. Set in 14K gold vermeil.",
            39.99,
            ["14K Gold Vermeil", "12 Options", "Stackable"],
            "birthstone-ring",
        ),
        (
            "Cufflink & Tie Bar Set",
            "Brushed stainless steel cufflinks and tie bar in a walnut presentation box.",
            54.99,
            ["Stainless Steel", "Walnut Box", "Brushed Finish"],
            "cufflinks",
        ),
        (
            "Crystal Tennis Bracelet",
            "Rhodium-plated tennis bracelet with brilliant-cut cubic zirconia stones.",
            69.99,
            ["Rhodium Plated", "CZ Stones", "Box Clasp"],
            "tennis-bracelet",
        ),
        (
            "Smart Hybrid Watch",
            "Analog watch face with smart notifications, step tracking, and 6-month battery.",
            199.99,
            ["Analog + Smart", "Notifications", "6-Month Battery"],
            "hybrid-watch",
        ),
    ],
    "cat-food-gourmet": [
        (
            "Artisan Chocolate Truffle Box",
            "24-piece collection of handmade Belgian chocolate truffles in assorted flavors.",
            34.99,
            ["24 Pieces", "Belgian Chocolate", "Handmade"],
            "chocolate-truffles",
        ),
        (
            "Holiday Cookie Gift Tin",
            "2 lb tin of assorted butter cookies in festive holiday shapes.",
            22.99,
            ["2 lb Tin", "Butter Cookies", "Holiday Shapes"],
            "cookie-tin",
        ),
        (
            "Single-Origin Coffee Sampler",
            "Set of four 4 oz bags of specialty single-origin coffees from around the world.",
            29.99,
            ["4 Origins", "Whole Bean", "Freshly Roasted"],
            "coffee-sampler",
        ),
        (
            "Gourmet Cheese Board Set",
            "Artisan cheese selection with crackers, fig jam, and bamboo serving board.",
            49.99,
            ["4 Cheeses", "Bamboo Board", "Fig Jam"],
            "cheese-board",
        ),
        (
            "Organic Tea Collection",
            "Gift box of 60 organic tea bags in 6 flavors: chamomile, green, earl grey, peppermint, chai, and rooibos.",
            19.99,
            ["60 Bags", "6 Flavors", "Organic"],
            "tea-collection",
        ),
        (
            "Hot Sauce Trio",
            "Set of three small-batch hot sauces: smoky chipotle, habanero mango, and ghost pepper.",
            24.99,
            ["3 Bottles", "Small Batch", "Varying Heat"],
            "hot-sauce",
        ),
        (
            "Olive Oil & Vinegar Set",
            "Premium extra-virgin olive oil and aged balsamic vinegar in glass bottles.",
            32.99,
            ["Extra Virgin", "Aged Balsamic", "Glass Bottles"],
            "olive-oil-set",
        ),
        (
            "Holiday Nuts & Dried Fruit Basket",
            "Gift basket with roasted almonds, cashews, dried cranberries, and apricots.",
            27.99,
            ["Mixed Nuts", "Dried Fruit", "Gift Basket"],
            "nuts-basket",
        ),
        (
            "Craft Beer Advent Calendar",
            "24 craft beers from independent breweries, one for each day of December.",
            59.99,
            ["24 Beers", "Independent Breweries", "Advent Calendar"],
            "beer-advent",
        ),
        (
            "Maple Syrup Gift Set",
            "Three-bottle set of grade A maple syrup: amber, dark, and very dark.",
            28.99,
            ["Grade A", "3 Bottles", "Vermont Maple"],
            "maple-syrup",
        ),
    ],
    "cat-pet-supplies": [
        (
            "Orthopedic Dog Bed Large",
            "Memory foam dog bed with waterproof liner and removable washable cover.",
            59.99,
            ["Memory Foam", "Waterproof Liner", "Washable Cover"],
            "dog-bed",
        ),
        (
            "Interactive Cat Puzzle Feeder",
            "Slow-feeder puzzle toy that stimulates your cat's natural hunting instincts.",
            19.99,
            ["Slow Feeder", "BPA Free", "Dishwasher Safe"],
            "cat-puzzle",
        ),
        (
            "Premium Grain-Free Dog Food 15 lb",
            "All-natural grain-free kibble with real salmon as the first ingredient.",
            49.99,
            ["Grain Free", "Real Salmon", "15 lb Bag"],
            "dog-food",
        ),
        (
            "Retractable Dog Leash 16 ft",
            "One-handed retractable leash with anti-slip handle and reflective cord.",
            22.99,
            ["16 ft", "Retractable", "Reflective"],
            "dog-leash",
        ),
        (
            "Cat Tower 5-Level",
            "Multi-level cat tree with sisal scratching posts, hammock, and plush perches.",
            79.99,
            ["5 Levels", "Sisal Posts", "Hammock"],
            "cat-tower",
        ),
        (
            "Pet Grooming Glove",
            "De-shedding grooming glove that works for cats and dogs. Gentle massage tips.",
            12.99,
            ["Cats & Dogs", "De-Shedding", "Massage Tips"],
            "grooming-glove",
        ),
        (
            "Automatic Pet Water Fountain",
            "2 L circulating water fountain with triple filtration and ultra-quiet pump.",
            29.99,
            ["2 L Capacity", "Triple Filter", "Ultra Quiet"],
            "water-fountain",
        ),
        (
            "Holiday Pet Outfit Set",
            "Festive holiday costume set with Santa hat, bandana, and bow tie for dogs.",
            18.99,
            ["3-Piece Set", "Adjustable", "Machine Washable"],
            "pet-costume",
        ),
        (
            "GPS Pet Tracker",
            "Lightweight GPS tracker for collars with real-time location and activity monitoring.",
            44.99,
            ["Real-Time GPS", "Activity Monitor", "Lightweight"],
            "pet-tracker",
        ),
        (
            "Natural Catnip Toy Bundle",
            "Set of 5 organic catnip toys in assorted shapes with crinkle filling.",
            14.99,
            ["5 Toys", "Organic Catnip", "Crinkle Filling"],
            "catnip-toys",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Demo users — synthetic customers for orders, reviews, tickets, etc.
# ---------------------------------------------------------------------------

DEMO_USERS: list[dict] = [
    {
        "id": "usr-001",
        "entra_id": "00000000-demo-0001-0000-000000000001",
        "email": "sarah.chen@example.com",
        "name": "Sarah Chen",
        "phone": "+1-555-0101",
    },
    {
        "id": "usr-002",
        "entra_id": "00000000-demo-0002-0000-000000000002",
        "email": "marcus.johnson@example.com",
        "name": "Marcus Johnson",
        "phone": "+1-555-0102",
    },
    {
        "id": "usr-003",
        "entra_id": "00000000-demo-0003-0000-000000000003",
        "email": "emily.taylor@example.com",
        "name": "Emily Taylor",
        "phone": "+1-555-0103",
    },
    {
        "id": "usr-004",
        "entra_id": "00000000-demo-0004-0000-000000000004",
        "email": "david.martinez@example.com",
        "name": "David Martinez",
        "phone": "+1-555-0104",
    },
    {
        "id": "usr-005",
        "entra_id": "00000000-demo-0005-0000-000000000005",
        "email": "olivia.patel@example.com",
        "name": "Olivia Patel",
        "phone": "+1-555-0105",
    },
    {
        "id": "usr-006",
        "entra_id": "00000000-demo-0006-0000-000000000006",
        "email": "james.kim@example.com",
        "name": "James Kim",
        "phone": "+1-555-0106",
    },
    {
        "id": "usr-007",
        "entra_id": "00000000-demo-0007-0000-000000000007",
        "email": "rachel.nguyen@example.com",
        "name": "Rachel Nguyen",
        "phone": None,
    },
    {
        "id": "usr-008",
        "entra_id": "00000000-demo-0008-0000-000000000008",
        "email": "chris.anderson@example.com",
        "name": "Chris Anderson",
        "phone": "+1-555-0108",
    },
    {
        "id": "usr-009",
        "entra_id": "00000000-demo-0009-0000-000000000009",
        "email": "mia.thompson@example.com",
        "name": "Mia Thompson",
        "phone": "+1-555-0109",
    },
    {
        "id": "usr-010",
        "entra_id": "00000000-demo-0010-0000-000000000010",
        "email": "alex.garcia@example.com",
        "name": "Alex Garcia",
        "phone": "+1-555-0110",
    },
]

# ---------------------------------------------------------------------------
# Demo orders — spread across users, products, and statuses
# ---------------------------------------------------------------------------

_CARRIERS = ["FedEx", "UPS", "USPS", "DHL Express"]

# Each entry: (order_id, user_id, items[(product_id, qty, price)], status,
#               days_ago, shipping_address_id, payment_method_id)
_DEMO_ORDERS_RAW: list[tuple[str, str, list[tuple[str, int, float]], str, int, str, str]] = [
    # Recent pending orders
    (
        "ord-001",
        "usr-001",
        [("prd-electronics-001", 1, 179.99), ("prd-electronics-003", 1, 349.99)],
        "pending",
        0,
        "addr-001",
        "pm-001",
    ),
    (
        "ord-002",
        "usr-003",
        [("prd-clothing-002", 2, 89.99), ("prd-clothing-005", 1, 54.99)],
        "pending",
        1,
        "addr-003",
        "pm-003",
    ),
    # Confirmed, waiting to ship
    (
        "ord-003",
        "usr-002",
        [("prd-home-kitchen-001", 1, 249.99)],
        "confirmed",
        2,
        "addr-002",
        "pm-002",
    ),
    (
        "ord-004",
        "usr-005",
        [
            ("prd-beauty-health-003", 3, 42.99),
            ("prd-beauty-health-007", 1, 64.99),
        ],
        "confirmed",
        3,
        "addr-005",
        "pm-005",
    ),
    # Shipped, in transit
    (
        "ord-005",
        "usr-004",
        [("prd-toys-games-001", 1, 159.99), ("prd-toys-games-004", 2, 34.99)],
        "shipped",
        5,
        "addr-004",
        "pm-004",
    ),
    (
        "ord-006",
        "usr-006",
        [("prd-sports-outdoors-002", 1, 299.99)],
        "shipped",
        4,
        "addr-006",
        "pm-006",
    ),
    (
        "ord-007",
        "usr-001",
        [
            ("prd-jewelry-watches-001", 1, 189.99),
            ("prd-jewelry-watches-005", 1, 79.99),
        ],
        "shipped",
        6,
        "addr-001",
        "pm-001",
    ),
    # Delivered
    (
        "ord-008",
        "usr-007",
        [("prd-books-media-001", 2, 28.99), ("prd-books-media-006", 1, 34.99)],
        "delivered",
        14,
        "addr-007",
        "pm-007",
    ),
    (
        "ord-009",
        "usr-008",
        [("prd-food-gourmet-002", 1, 54.99), ("prd-food-gourmet-005", 2, 38.99)],
        "delivered",
        10,
        "addr-008",
        "pm-008",
    ),
    (
        "ord-010",
        "usr-002",
        [("prd-pet-supplies-001", 1, 59.99), ("prd-pet-supplies-006", 1, 44.99)],
        "delivered",
        21,
        "addr-002",
        "pm-002",
    ),
    (
        "ord-011",
        "usr-009",
        [("prd-electronics-005", 1, 899.99)],
        "delivered",
        18,
        "addr-009",
        "pm-009",
    ),
    (
        "ord-012",
        "usr-010",
        [
            ("prd-home-kitchen-004", 1, 89.99),
            ("prd-home-kitchen-008", 2, 32.99),
        ],
        "delivered",
        25,
        "addr-010",
        "pm-010",
    ),
    (
        "ord-013",
        "usr-003",
        [
            ("prd-clothing-001", 1, 129.99),
            ("prd-sports-outdoors-005", 1, 44.99),
        ],
        "delivered",
        30,
        "addr-003",
        "pm-003",
    ),
    (
        "ord-014",
        "usr-005",
        [("prd-toys-games-006", 1, 54.99), ("prd-toys-games-009", 1, 29.99)],
        "delivered",
        35,
        "addr-005",
        "pm-005",
    ),
    (
        "ord-015",
        "usr-004",
        [("prd-electronics-008", 1, 129.99)],
        "delivered",
        45,
        "addr-004",
        "pm-004",
    ),
    # Cancelled
    (
        "ord-016",
        "usr-006",
        [("prd-jewelry-watches-003", 1, 599.99)],
        "cancelled",
        7,
        "addr-006",
        "pm-006",
    ),
    (
        "ord-017",
        "usr-008",
        [("prd-electronics-002", 1, 999.99)],
        "cancelled",
        12,
        "addr-008",
        "pm-008",
    ),
    # Additional delivered orders for review variety
    (
        "ord-018",
        "usr-001",
        [("prd-beauty-health-001", 1, 48.99)],
        "delivered",
        40,
        "addr-001",
        "pm-001",
    ),
    (
        "ord-019",
        "usr-007",
        [("prd-food-gourmet-001", 1, 42.99)],
        "delivered",
        28,
        "addr-007",
        "pm-007",
    ),
    (
        "ord-020",
        "usr-009",
        [("prd-clothing-003", 1, 199.99), ("prd-clothing-007", 1, 149.99)],
        "delivered",
        22,
        "addr-009",
        "pm-009",
    ),
]

# ---------------------------------------------------------------------------
# Demo reviews — curated across products and users
# Each entry: (review_id, product_id, user_id, rating, title, comment, days_ago)
# ---------------------------------------------------------------------------

DEMO_REVIEWS: list[tuple[str, str, str, int, str, str, int]] = [
    # Electronics
    (
        "rev-001",
        "prd-electronics-001",
        "usr-007",
        5,
        "Best headphones I've owned",
        "The noise cancellation is incredible. I can finally work from the coffee shop without distractions. Battery lasts well over the claimed 30 hours.",
        12,
    ),
    (
        "rev-002",
        "prd-electronics-001",
        "usr-002",
        4,
        "Great sound, slightly tight fit",
        "Audio quality is outstanding for the price. My only complaint is they feel a bit tight after 3+ hours. Noise cancellation works really well on flights.",
        20,
    ),
    (
        "rev-003",
        "prd-electronics-002",
        "usr-009",
        5,
        "MacBook Pro replacement?",
        "This laptop seriously competes with machines twice the price. The display is gorgeous, and it handles my development workflows without breaking a sweat.",
        15,
    ),
    (
        "rev-004",
        "prd-electronics-005",
        "usr-009",
        5,
        "Perfect home theater upgrade",
        "Replaced my old soundbar and the difference is night and day. The Dolby Atmos support makes movies feel like a cinema experience.",
        16,
    ),
    (
        "rev-005",
        "prd-electronics-008",
        "usr-004",
        4,
        "Solid portable speaker",
        "Great battery life and surprisingly loud. Took it camping and it survived a light rain. Bass could be a bit deeper for the price, but overall very happy.",
        42,
    ),
    # Clothing
    (
        "rev-006",
        "prd-clothing-001",
        "usr-003",
        5,
        "My go-to winter jacket",
        "Warm without being bulky. I've worn it in below-freezing temps and stayed comfortable. The pockets are well-placed and the hood stays put in wind.",
        28,
    ),
    (
        "rev-007",
        "prd-clothing-002",
        "usr-003",
        4,
        "Beautiful holiday sweater",
        "Got so many compliments at the office party. The merino wool is soft and doesn't itch. Runs slightly large — consider sizing down.",
        25,
    ),
    (
        "rev-008",
        "prd-clothing-003",
        "usr-009",
        5,
        "Dress to impress",
        "Wore this to a holiday gala and received nothing but compliments. The velvet fabric drapes beautifully and the tailoring is impeccable for this price point.",
        20,
    ),
    # Home & Kitchen
    (
        "rev-009",
        "prd-home-kitchen-001",
        "usr-002",
        5,
        "Restaurant-quality cookware",
        "Upgraded from a basic set and the difference is remarkable. Even heating, comfortable handles, and everything cleans up easily. Worth every penny.",
        30,
    ),
    (
        "rev-010",
        "prd-home-kitchen-004",
        "usr-010",
        4,
        "Great blender for the price",
        "Makes perfectly smooth smoothies and can handle frozen fruit without issue. It's a bit loud, but that's expected for the power it provides.",
        23,
    ),
    # Toys & Games
    (
        "rev-011",
        "prd-toys-games-001",
        "usr-004",
        5,
        "My kids are obsessed",
        "The build quality is excellent and the coding concepts are introduced gradually. Both my 7 and 10-year-old love it. Great educational gift.",
        32,
    ),
    (
        "rev-012",
        "prd-toys-games-004",
        "usr-004",
        4,
        "Fun for family game night",
        "Easy to learn but hard to master. We play it every Friday night now. Some card stock could be thicker, but the gameplay makes up for it.",
        33,
    ),
    # Sports & Outdoors
    (
        "rev-013",
        "prd-sports-outdoors-002",
        "usr-006",
        5,
        "Game changer for my fitness routine",
        "The automatic resistance adjustment is incredibly smooth. Syncs perfectly with multiple fitness apps. Compact enough for my apartment's spare room.",
        35,
    ),
    (
        "rev-014",
        "prd-sports-outdoors-005",
        "usr-003",
        4,
        "Perfect for morning runs",
        "Moisture-wicking fabric actually works. Pockets are well-placed for keys and phone. Wish they made more color options, but the quality is excellent.",
        28,
    ),
    # Beauty & Health
    (
        "rev-015",
        "prd-beauty-health-001",
        "usr-001",
        5,
        "Visible results in two weeks",
        "I was skeptical, but my skin genuinely looks brighter and more even after using the full set. The serum absorbs quickly and the moisturizer isn't greasy at all.",
        38,
    ),
    (
        "rev-016",
        "prd-beauty-health-003",
        "usr-005",
        4,
        "Lovely gift set",
        "Bought three of these as holiday gifts. The scents are subtle and natural, and the oil quality is excellent. Packaging is beautiful enough to not need wrapping.",
        29,
    ),
    # Books & Media
    (
        "rev-017",
        "prd-books-media-001",
        "usr-007",
        5,
        "Could not put it down",
        "Read it in two sittings. The world-building is extraordinary and the characters feel real. Already pre-ordered the sequel.",
        12,
    ),
    (
        "rev-018",
        "prd-books-media-006",
        "usr-007",
        4,
        "Beautiful vinyl pressing",
        "The 180-gram pressing sounds phenomenal on my turntable. Comes with great liner notes and a download card. Minor surface noise on one track, but excellent overall.",
        13,
    ),
    # Jewelry & Watches
    (
        "rev-019",
        "prd-jewelry-watches-001",
        "usr-001",
        5,
        "Elegant and affordable",
        "Bought this for my anniversary and my wife absolutely loves it. The craftsmanship looks much more expensive than it is. The sterling silver has held up beautifully.",
        40,
    ),
    (
        "rev-020",
        "prd-jewelry-watches-005",
        "usr-001",
        4,
        "Classy everyday watch",
        "Great minimalist design. The leather strap is comfortable and the automatic movement keeps good time. Crystal has a few micro-scratches after a month of daily wear.",
        39,
    ),
    # Food & Gourmet
    (
        "rev-021",
        "prd-food-gourmet-001",
        "usr-007",
        5,
        "Chocolate lover's dream",
        "Every piece is a different flavor journey. The dark chocolate truffle with sea salt is my new obsession. Arrived well-packaged and in perfect condition.",
        26,
    ),
    (
        "rev-022",
        "prd-food-gourmet-002",
        "usr-008",
        4,
        "Impressive gift basket",
        "Sent this to my parents and they were thrilled. Great variety of cheeses and crackers. The olive oil was a standout. One jar arrived with a loose lid but no spillage.",
        8,
    ),
    (
        "rev-023",
        "prd-food-gourmet-005",
        "usr-008",
        5,
        "Best coffee subscription start",
        "All three origins are distinct and delicious. The Ethiopian is fruity and bright, the Colombian is smooth, and the Sumatran is bold. Freshly roasted — you can tell.",
        9,
    ),
    # Pet Supplies
    (
        "rev-024",
        "prd-pet-supplies-001",
        "usr-002",
        5,
        "My dog sleeps through the night now",
        "Our golden retriever claimed this bed immediately. The orthopedic foam gives great support for his aging joints. The removable cover is a huge plus for washing.",
        19,
    ),
    (
        "rev-025",
        "prd-pet-supplies-006",
        "usr-002",
        4,
        "Cats love the tower",
        "Our two cats fight over who gets the top perch. Sturdy construction — doesn't wobble at all. Assembly took about 30 minutes. Wish the sisal posts were a bit thicker.",
        20,
    ),
]

# ---------------------------------------------------------------------------
# Demo support tickets
# Each entry: (ticket_id, user_id, subject, status, priority, days_ago)
# ---------------------------------------------------------------------------

DEMO_TICKETS: list[tuple[str, str, str, str, str, int]] = [
    (
        "tkt-001",
        "usr-001",
        "Order arrived with damaged packaging",
        "open",
        "high",
        1,
    ),
    (
        "tkt-002",
        "usr-003",
        "Request to change shipping address on pending order",
        "open",
        "medium",
        0,
    ),
    (
        "tkt-003",
        "usr-005",
        "Promo code not applying at checkout",
        "in_progress",
        "medium",
        3,
    ),
    (
        "tkt-004",
        "usr-002",
        "Missing item from delivered order",
        "in_progress",
        "high",
        5,
    ),
    (
        "tkt-005",
        "usr-008",
        "How to initiate a product return?",
        "resolved",
        "low",
        10,
    ),
    (
        "tkt-006",
        "usr-006",
        "Cancelled order still showing as pending",
        "resolved",
        "medium",
        8,
    ),
    (
        "tkt-007",
        "usr-004",
        "Item arrived different color than pictured",
        "open",
        "medium",
        2,
    ),
    (
        "tkt-008",
        "usr-009",
        "Requesting invoice for business purchase",
        "closed",
        "low",
        15,
    ),
    (
        "tkt-009",
        "usr-010",
        "Account shows wrong email address",
        "resolved",
        "high",
        12,
    ),
    (
        "tkt-010",
        "usr-007",
        "Tracking number not updating for 5 days",
        "in_progress",
        "critical",
        4,
    ),
    (
        "tkt-011",
        "usr-001",
        "Received wrong product — need exchange",
        "open",
        "high",
        1,
    ),
    (
        "tkt-012",
        "usr-004",
        "Gift card balance not reflecting after purchase",
        "in_progress",
        "medium",
        6,
    ),
]

# ---------------------------------------------------------------------------
# Demo returns — tied to delivered orders
# Each entry: (return_id, order_id, user_id, status, reason, days_ago)
# ---------------------------------------------------------------------------

DEMO_RETURNS: list[tuple[str, str, str, str, str, int]] = [
    (
        "ret-001",
        "ord-010",
        "usr-002",
        "pending",
        "Product did not match description — expected larger size",
        2,
    ),
    (
        "ret-002",
        "ord-011",
        "usr-009",
        "approved",
        "Minor cosmetic defect on device casing",
        8,
    ),
    (
        "ret-003",
        "ord-012",
        "usr-010",
        "completed",
        "Changed mind — house décor style changed",
        18,
    ),
    (
        "ret-004",
        "ord-013",
        "usr-003",
        "pending",
        "Jacket zipper broke after first wash",
        3,
    ),
    (
        "ret-005",
        "ord-015",
        "usr-004",
        "rejected",
        "Return requested outside return window",
        30,
    ),
    (
        "ret-006",
        "ord-008",
        "usr-007",
        "approved",
        "Received duplicate books — returning extras",
        5,
    ),
]


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _build_dsn() -> str:
    postgres_host = _required_env("POSTGRES_HOST")
    postgres_user = _required_env("POSTGRES_USER")
    postgres_password = _required_env("POSTGRES_PASSWORD")
    postgres_database = os.getenv("POSTGRES_DATABASE", "holiday_peak_crud")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_ssl = os.getenv("POSTGRES_SSL", "true").lower() == "true"
    sslmode = "require" if postgres_ssl else "disable"

    return (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_database}?sslmode={sslmode}"
    )


async def _connect_with_entra() -> tuple[asyncpg.Connection, DefaultAzureCredential]:
    postgres_host = _required_env("POSTGRES_HOST")
    postgres_user = _required_env("POSTGRES_USER")
    postgres_database = os.getenv("POSTGRES_DATABASE", "holiday_peak_crud")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_ssl = os.getenv("POSTGRES_SSL", "true").lower() == "true"
    postgres_entra_scope = os.getenv(
        "POSTGRES_ENTRA_SCOPE", "https://ossrdbms-aad.database.windows.net/.default"
    )

    credential = DefaultAzureCredential()
    token = await credential.get_token(postgres_entra_scope)
    conn = await asyncpg.connect(
        host=postgres_host,
        port=postgres_port,
        user=postgres_user,
        password=token.token,
        database=postgres_database,
        ssl="require" if postgres_ssl else None,
    )
    return conn, credential


async def _ensure_table(conn: asyncpg.Connection, table_name: str) -> None:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id TEXT PRIMARY KEY,
            partition_key TEXT,
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)
    await conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_partition_key ON {table_name}(partition_key)"
    )
    await conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_data_gin ON {table_name} USING GIN (data)"
    )


async def _upsert_item(
    conn: asyncpg.Connection,
    table_name: str,
    item_id: str,
    partition_key: str,
    item: dict,
) -> None:
    await conn.execute(
        f"""
        INSERT INTO {table_name} (id, partition_key, data, created_at, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW(), NOW())
        ON CONFLICT (id)
        DO UPDATE SET
            partition_key = EXCLUDED.partition_key,
            data = EXCLUDED.data,
            updated_at = NOW()
        """,
        item_id,
        partition_key,
        json.dumps(item),
    )


async def main() -> None:
    environment = os.getenv("DEMO_ENVIRONMENT", "dev")
    postgres_auth_mode = os.getenv("POSTGRES_AUTH_MODE", "password").strip().lower()

    credential: DefaultAzureCredential | None = None
    if postgres_auth_mode == "entra":
        conn, credential = await _connect_with_entra()
    else:
        dsn = _build_dsn()
        conn = await asyncpg.connect(dsn)
    rng = random.Random(42)

    try:
        # Ensure all tables exist
        for table in (
            "categories",
            "products",
            "users",
            "orders",
            "shipments",
            "reviews",
            "tickets",
            "returns",
        ):
            await _ensure_table(conn, table)

        now_dt = datetime.now(UTC)
        now = now_dt.isoformat()

        # ------------------------------------------------------------------
        # 1. Seed categories
        # ------------------------------------------------------------------
        for cat in CATEGORIES:
            category = {
                **cat,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="categories",
                item_id=cat["id"],
                partition_key=cat["id"],
                item=category,
            )

        # ------------------------------------------------------------------
        # 2. Seed products
        # ------------------------------------------------------------------
        product_count = 0
        for category_id, products in _PRODUCTS_BY_CATEGORY.items():
            for idx, (name, description, price, features, img_kw) in enumerate(products, start=1):
                product_count += 1
                product_id = f"prd-{category_id.removeprefix('cat-')}-{idx:03d}"
                in_stock = rng.choice([True, True, True, False])

                product = {
                    "id": product_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "category_id": category_id,
                    "image_url": (
                        f"https://images.unsplash.com/photo-{img_kw}" f"?w=800&q=80&fit=crop"
                    ),
                    "in_stock": in_stock,
                    "rating": round(rng.uniform(3.8, 5.0), 1),
                    "review_count": rng.randint(12, 850),
                    "features": features,
                    "seeded": True,
                    "environment": environment,
                    "updated_at": now,
                }

                await _upsert_item(
                    conn=conn,
                    table_name="products",
                    item_id=product_id,
                    partition_key=category_id,
                    item=product,
                )

        # ------------------------------------------------------------------
        # 3. Seed users
        # ------------------------------------------------------------------
        for usr in DEMO_USERS:
            user = {
                **usr,
                "created_at": (now_dt - timedelta(days=rng.randint(60, 180))).isoformat(),
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="users",
                item_id=usr["id"],
                partition_key=usr["id"],
                item=user,
            )

        # ------------------------------------------------------------------
        # 4. Seed orders
        # ------------------------------------------------------------------
        order_count = 0
        for (
            order_id,
            user_id,
            raw_items,
            status,
            days_ago,
            addr_id,
            pm_id,
        ) in _DEMO_ORDERS_RAW:
            order_count += 1
            items = [
                {"product_id": pid, "quantity": qty, "price": price}
                for pid, qty, price in raw_items
            ]
            total = round(sum(i["price"] * i["quantity"] for i in items), 2)
            created_at = (now_dt - timedelta(days=days_ago)).isoformat()

            order = {
                "id": order_id,
                "user_id": user_id,
                "items": items,
                "total": total,
                "status": status,
                "shipping_address_id": addr_id,
                "payment_method_id": pm_id,
                "created_at": created_at,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="orders",
                item_id=order_id,
                partition_key=user_id,
                item=order,
            )

        # ------------------------------------------------------------------
        # 5. Seed shipments (for shipped + delivered orders)
        # ------------------------------------------------------------------
        shipment_count = 0
        for (
            order_id,
            user_id,
            _raw_items,
            status,
            days_ago,
            _addr,
            _pm,
        ) in _DEMO_ORDERS_RAW:
            if status not in ("shipped", "delivered"):
                continue
            shipment_count += 1
            carrier = rng.choice(_CARRIERS)
            tracking = (
                f"{carrier[:3].upper()}-"
                f"{uuid.uuid5(uuid.NAMESPACE_DNS, order_id).hex[:12].upper()}"
            )
            ship_status = "delivered" if status == "delivered" else "in_transit"
            ship_id = f"shp-{order_id.removeprefix('ord-')}"
            created_at = (now_dt - timedelta(days=max(days_ago - 1, 0))).isoformat()

            shipment = {
                "id": ship_id,
                "order_id": order_id,
                "status": ship_status,
                "carrier": carrier,
                "tracking_number": tracking,
                "created_at": created_at,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="shipments",
                item_id=ship_id,
                partition_key=order_id,
                item=shipment,
            )

        # ------------------------------------------------------------------
        # 6. Seed reviews
        # ------------------------------------------------------------------
        for (
            rev_id,
            product_id,
            user_id,
            rating,
            title,
            comment,
            days_ago,
        ) in DEMO_REVIEWS:
            created_at = (now_dt - timedelta(days=days_ago)).isoformat()
            review = {
                "id": rev_id,
                "product_id": product_id,
                "user_id": user_id,
                "rating": rating,
                "title": title,
                "comment": comment,
                "created_at": created_at,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="reviews",
                item_id=rev_id,
                partition_key=user_id,
                item=review,
            )

        # ------------------------------------------------------------------
        # 7. Seed tickets
        # ------------------------------------------------------------------
        for (
            tkt_id,
            user_id,
            subject,
            status,
            priority,
            days_ago,
        ) in DEMO_TICKETS:
            created_at = (now_dt - timedelta(days=days_ago)).isoformat()
            ticket = {
                "id": tkt_id,
                "user_id": user_id,
                "subject": subject,
                "status": status,
                "priority": priority,
                "created_at": created_at,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="tickets",
                item_id=tkt_id,
                partition_key=user_id,
                item=ticket,
            )

        # ------------------------------------------------------------------
        # 8. Seed returns
        # ------------------------------------------------------------------
        for (
            ret_id,
            order_id,
            user_id,
            status,
            reason,
            days_ago,
        ) in DEMO_RETURNS:
            created_at = (now_dt - timedelta(days=days_ago)).isoformat()
            ret = {
                "id": ret_id,
                "order_id": order_id,
                "user_id": user_id,
                "status": status,
                "reason": reason,
                "created_at": created_at,
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }
            await _upsert_item(
                conn=conn,
                table_name="returns",
                item_id=ret_id,
                partition_key=user_id,
                item=ret,
            )

        print(
            f"Seed completed for environment={environment}: "
            f"categories={len(CATEGORIES)}, products={product_count}, "
            f"users={len(DEMO_USERS)}, orders={order_count}, "
            f"shipments={shipment_count}, reviews={len(DEMO_REVIEWS)}, "
            f"tickets={len(DEMO_TICKETS)}, returns={len(DEMO_RETURNS)}"
        )
    finally:
        await conn.close()
        if credential is not None:
            await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
