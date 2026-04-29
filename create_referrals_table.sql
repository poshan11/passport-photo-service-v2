-- Create referrals table for customer referral system
CREATE TABLE IF NOT EXISTS referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    referral_remaining INT DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_email (email),
    INDEX idx_referral_remaining (referral_remaining),
    
    -- Constraints
    CONSTRAINT chk_positive_remaining CHECK (referral_remaining >= 0),
    CONSTRAINT chk_valid_email CHECK (email REGEXP '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')
);

-- Optional: Add some sample data for testing
-- INSERT INTO referrals (email, referral_remaining) VALUES 
-- ('test@gmail.com', 3),
-- ('existing@gmail.com', 5);
