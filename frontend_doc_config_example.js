/**
 * Frontend Document Configuration Utility
 * 
 * This demonstrates the new simplified approach where:
 * 1. Frontend calculates exact pixel dimensions from physical measurements
 * 2. Backend uses these dimensions directly without any conversions
 * 3. No more target_size + aspect_ratio complexity
 * 
 * Usage in your PassportPhotoMaker frontend:
 * 
 * import { createDocumentConfig, mmToPixels, inchesToPixels } from './documentConfigUtils';
 * 
 * const config = createDocumentConfig({
 *   widthMM: 35,
 *   heightMM: 45,
 *   dpi: 300,
 *   isBabyPhoto: false
 * });
 */

/**
 * Convert millimeters to pixels at specified DPI
 * @param {number} mm - Millimeters 
 * @param {number} dpi - Dots per inch (default: 300)
 * @returns {number} Pixels
 */
function mmToPixels(mm, dpi = 300) {
    return Math.round((mm * dpi) / 25.4);
}

/**
 * Convert inches to pixels at specified DPI
 * @param {number} inches - Inches
 * @param {number} dpi - Dots per inch (default: 300) 
 * @returns {number} Pixels
 */
function inchesToPixels(inches, dpi = 300) {
    return Math.round(inches * dpi);
}

/**
 * Create document configuration for the backend
 * This replaces the old target_size + aspect_ratio approach
 * 
 * @param {Object} params - Configuration parameters
 * @param {number} [params.widthMM] - Width in millimeters
 * @param {number} [params.heightMM] - Height in millimeters  
 * @param {number} [params.widthInches] - Width in inches
 * @param {number} [params.heightInches] - Height in inches
 * @param {number} [params.finalWidth] - Direct pixel width (overrides other width params)
 * @param {number} [params.finalHeight] - Direct pixel height (overrides other height params)
 * @param {number} [params.dpi=300] - Dots per inch for conversion
 * @param {string} [params.background='white'] - Background color
 * @param {boolean} [params.isBabyPhoto=false] - Whether this is for a baby
 * @returns {Object} Document configuration for backend
 */
function createDocumentConfig({
    widthMM,
    heightMM,
    widthInches,
    heightInches,
    finalWidth,
    finalHeight,
    dpi = 300,
    background = 'white',
    isBabyPhoto = false
}) {
    let final_width, final_height;
    
    // Priority: direct pixels > inches > millimeters
    if (finalWidth && finalHeight) {
        final_width = finalWidth;
        final_height = finalHeight;
    } else if (widthInches && heightInches) {
        final_width = inchesToPixels(widthInches, dpi);
        final_height = inchesToPixels(heightInches, dpi);
    } else if (widthMM && heightMM) {
        final_width = mmToPixels(widthMM, dpi);
        final_height = mmToPixels(heightMM, dpi);
    } else {
        throw new Error('Must provide either finalWidth/finalHeight, widthInches/heightInches, or widthMM/heightMM');
    }
    
    return {
        final_width: final_width,
        final_height: final_height,
        background: background,
        head_ratio: isBabyPhoto ? 0.6 : 0.7,
        eye_level: isBabyPhoto ? 0.55 : 0.6
    };
}

/**
 * Predefined document type configurations
 * Use these for common document types
 */
const DOCUMENT_PRESETS = {
    // US Documents
    us_passport: () => createDocumentConfig({ widthInches: 2, heightInches: 2 }),
    us_visa: () => createDocumentConfig({ widthInches: 2, heightInches: 2 }),
    real_id: () => createDocumentConfig({ widthInches: 2, heightInches: 2 }),
    uscis: () => createDocumentConfig({ widthInches: 2, heightInches: 2 }),
    green_card: () => createDocumentConfig({ widthInches: 2, heightInches: 2 }),
    
    // International Documents  
    uk_passport: () => createDocumentConfig({ widthMM: 35, heightMM: 45 }),
    canada_passport: () => createDocumentConfig({ widthMM: 50, heightMM: 70 }),
    australia_visa: () => createDocumentConfig({ widthMM: 35, heightMM: 45 }),
    japan_passport: () => createDocumentConfig({ widthMM: 35, heightMM: 45 }),
    french_passport: () => createDocumentConfig({ widthMM: 35, heightMM: 45 }),
    
    // Visa Documents
    chinese_visa: () => createDocumentConfig({ widthMM: 33, heightMM: 48 }),
    uae_visa: () => createDocumentConfig({ widthMM: 43, heightMM: 55 }),
    
    // Other
    vietnam_passport: () => createDocumentConfig({ widthMM: 40, heightMM: 60 }),
    turkish_passport: () => createDocumentConfig({ widthMM: 50, heightMM: 60 }),
    
    // Baby versions
    baby_passport: () => createDocumentConfig({ widthInches: 2, heightInches: 2, isBabyPhoto: true })
};

/**
 * Get document configuration by type
 * @param {string} docType - Document type
 * @returns {Object} Document configuration
 */
function getDocumentConfig(docType) {
    const preset = DOCUMENT_PRESETS[docType];
    if (!preset) {
        console.warn(`Unknown document type: ${docType}. Using default.`);
        return createDocumentConfig({ widthInches: 2, heightInches: 2 });
    }
    return preset();
}

/**
 * Example: How to handle custom size in your frontend
 * @param {number} customWidth - Custom width in mm
 * @param {number} customHeight - Custom height in mm
 * @param {number} dpi - DPI setting
 * @param {boolean} isBabyPhoto - Baby photo flag
 * @returns {Object} Custom document configuration
 */
function createCustomSizeConfig(customWidth, customHeight, dpi = 300, isBabyPhoto = false) {
    return createDocumentConfig({
        widthMM: customWidth,
        heightMM: customHeight,
        dpi: dpi,
        isBabyPhoto: isBabyPhoto
    });
}

/**
 * Example: Send to backend API
 * This is how you would use it in your actual frontend code
 */
function processImageWithCustomSize(imageFile, customWidth, customHeight) {
    // Create the document configuration
    const docConfig = createCustomSizeConfig(customWidth, customHeight);
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', imageFile);
    formData.append('docType', 'custom_size');
    formData.append('docConfig', JSON.stringify(docConfig));
    
    // Send to backend
    return fetch('/process', {
        method: 'POST',
        body: formData
    });
}

/**
 * Example: Process with predefined document type
 */
function processImageWithDocumentType(imageFile, docType) {
    // Get the predefined configuration
    const docConfig = getDocumentConfig(docType);
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', imageFile);
    formData.append('docType', docType);
    formData.append('docConfig', JSON.stringify(docConfig));
    
    // Send to backend
    return fetch('/process', {
        method: 'POST',
        body: formData
    });
}

// Export for use in your frontend
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        mmToPixels,
        inchesToPixels,
        createDocumentConfig,
        getDocumentConfig,
        createCustomSizeConfig,
        processImageWithCustomSize,
        processImageWithDocumentType,
        DOCUMENT_PRESETS
    };
}

// Example usage and testing
if (typeof window !== 'undefined') {
    console.log('=== Frontend Document Configuration Examples ===');
    
    // Example 1: UK Passport (35x45mm)
    const ukConfig = getDocumentConfig('uk_passport');
    console.log('UK Passport:', ukConfig);
    // Output: { final_width: 413, final_height: 531, background: 'white', head_ratio: 0.7, eye_level: 0.6 }
    
    // Example 2: US Passport (2x2 inches)
    const usConfig = getDocumentConfig('us_passport');  
    console.log('US Passport:', usConfig);
    // Output: { final_width: 600, final_height: 600, background: 'white', head_ratio: 0.7, eye_level: 0.6 }
    
    // Example 3: Custom size (40x50mm)
    const customConfig = createCustomSizeConfig(40, 50);
    console.log('Custom 40x50mm:', customConfig);
    // Output: { final_width: 472, final_height: 591, background: 'white', head_ratio: 0.7, eye_level: 0.6 }
    
    // Example 4: High DPI custom size
    const highDpiConfig = createCustomSizeConfig(35, 45, 600); // 600 DPI
    console.log('35x45mm at 600 DPI:', highDpiConfig);
    // Output: { final_width: 827, final_height: 1063, background: 'white', head_ratio: 0.7, eye_level: 0.6 }
}
