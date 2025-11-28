# 3.4 Dataset Used

The project used six primary datasets to train, test, and evaluate different modules of AI-MedPay:

---

## A. Insurance Plan Dataset

This dataset contains information about publicly available health insurance policies.
It was compiled from government health portals, open data repositories, and sample insurer APIs.
Each record represents a unique insurance plan with attributes such as:

| Feature                   | Description                                                            |
| ------------------------- | ---------------------------------------------------------------------- |
| **Plan ID**               | Unique identifier for the policy (e.g., PL10000, PL10001)              |
| **Provider**              | Name of the insurance company (e.g., LIC, HDFC Life, ICICI Prudential) |
| **Plan Name**             | Full name of the insurance plan                                        |
| **Premium**               | Monthly or annual cost of the plan (in INR)                            |
| **Deductible**            | Amount policyholder pays before insurance coverage begins              |
| **Co-pay Ratio**          | Percentage of the bill paid by the policyholder                        |
| **Coverage Amount**       | Maximum coverage amount (Sum Insured)                                  |
| **Network Size**          | Count of hospitals covered under the plan                              |
| **Claim Rejection Rate**  | Percentage of rejected claims (inverse of claim settlement ratio)      |
| **Add-ons**               | Optional coverage details (accident cover, ambulance, daycare, etc.)   |
| **Waiting Period (Days)** | Time before pre-existing diseases are covered                          |
| **Geos**                  | Geographic regions where the plan is available                         |
| **Plan Type**             | Classification of plan (individual, family, etc.)                      |
| **Plan Tier**             | Premium tier classification                                            |
| **Age Band Premiums**     | Different premiums for age groups (18-35, 36-50, 51-65)                |
| **Max Out of Pocket**     | Maximum amount the policyholder will pay annually                      |
| **Plan Category**         | Type of plan (Pure Term, TROP, Convertible Term, etc.)                 |

**Data Characteristics:**

- This dataset was cleaned and normalized into 18 numerical and categorical features.
- It was used to train the **LightGBM plan ranking model**, which predicts how suitable each plan is for a user profile.
- The ground-truth target scores were generated using expert-curated rankings and simulated user preference data.

**Dataset Specifications:**

- **Size:** ~206 records × 18 features
- **Format:** CSV
- **Source:** Government insurance datasets, IRDAI open data, and synthetic augmentation for testing
- **File Location:** `backend/data/plans.csv`

**Sample Coverage Amounts:**

- Range: ₹500,000 to ₹20,000,000
- Premium Range: ₹15 to ₹600 per month/year

---

## B. User Profile Dataset

This dataset contains comprehensive user demographic and health information for personalized plan recommendations.
Each record represents a unique user with their complete health and financial profile.

| Feature                    | Description                                                                |
| -------------------------- | -------------------------------------------------------------------------- |
| **User ID**                | Unique identifier for each user (e.g., U0001, U0002)                       |
| **Age**                    | User's age in years                                                        |
| **Gender**                 | Gender classification (male, female, other)                                |
| **Marital Status**         | Marital status (single, married, divorced, widowed)                        |
| **Occupation**             | Employment type (salaried, self-employed, retired, student, homemaker)     |
| **Income Band**            | Annual income range (<3L, 3-6L, 6-10L, 10-20L, >20L)                       |
| **Urban/Rural**            | Residential area type (urban, semi-urban, rural)                           |
| **Region**                 | State of residence                                                         |
| **Dependents**             | Number of family dependents                                                |
| **Digital Literacy**       | Level of digital comfort (low, medium, high)                               |
| **Preferred Payment Mode** | Payment preference (monthly, quarterly, annual)                            |
| **Preferred Providers**    | List of preferred insurance providers                                      |
| **Avg Annual Spend**       | Average annual healthcare expenditure (in INR)                             |
| **Risk Score**             | Calculated health risk score (0-1 scale)                                   |
| **Chronic Conditions**     | Pre-existing chronic conditions                                            |
| **Family Medical History** | Family history of diseases (diabetes, hypertension, cancer, heart disease) |
| **Existing Health Policy** | Whether user has current insurance (yes/no)                                |
| **Claim History Count**    | Number of previous insurance claims                                        |
| **Renewal Loyalty Years**  | Years with current insurance provider                                      |
| **Health Flags**           | Binary flags for specific conditions:                                      |
| - Has Diabetes             | Diabetes diagnosis status                                                  |
| - Has Hypertension         | Hypertension diagnosis status                                              |
| - Has Asthma               | Asthma diagnosis status                                                    |
| - Has Cancer History       | Cancer diagnosis history                                                   |
| - Has Heart Disease        | Heart disease diagnosis status                                             |
| - Has Thyroid              | Thyroid disorder status                                                    |
| - Has Kidney Disease       | Kidney disease status                                                      |
| - Has Obesity              | Obesity classification                                                     |
| - Has Disability           | Disability status                                                          |
| **Smoking Status**         | Smoking habit (smoker, non-smoker, ex-smoker)                              |

**Data Characteristics:**

- Used for personalized plan recommendation and risk assessment
- Features include demographic, financial, and health attributes
- Enables the recommendation engine to match users with suitable plans

**Dataset Specifications:**

- **Size:** ~502 records × 29 features
- **Format:** CSV
- **Source:** Synthetic user profiles with realistic distributions
- **File Location:** `backend/data/users.csv`

**Sample Demographics:**

- Age Range: 19-74 years
- Income Bands: Distributed across all categories
- Geographic Coverage: All major Indian states

---

## C. Medical Procedures Dataset

This dataset contains comprehensive information about common medical procedures and their associated costs.
It serves as a reference for cost estimation and claim processing.

| Feature               | Description                                          |
| --------------------- | ---------------------------------------------------- |
| **Procedure Code**    | Unique identifier for each medical procedure         |
| **Procedure Name**    | Full name of the medical procedure or treatment      |
| **Average Cost**      | Mean cost of the procedure across hospitals (in INR) |
| **Typical Cost Low**  | Lower bound of typical procedure cost                |
| **Typical Cost High** | Upper bound of typical procedure cost                |
| **Common Hospitals**  | List of hospitals commonly performing this procedure |

**Procedure Categories Covered:**

1. **Major Surgeries:** Knee Replacement, Hip Replacement, CABG, Angioplasty
2. **Minor Surgeries:** Hernia Repair, Appendectomy, Gallbladder Removal
3. **Cardiac Procedures:** Cardiac Catheterization, Pacemaker Implant
4. **Imaging & Diagnostics:** MRI, CT Scan, PET-CT, X-Ray, Ultrasound, Mammography
5. **Endoscopic Procedures:** Endoscopy, Colonoscopy
6. **Maternity Services:** Normal Delivery, C-Section, IVF Cycle
7. **Oncology:** Chemotherapy, Radiotherapy, Cancer Surgeries
8. **Orthopedic:** ACL Repair, Shoulder Rotator Cuff Repair
9. **Transplants:** Liver Transplant, Kidney Transplant
10. **ICU & Hospitalization:** ICU Stay, General Ward, NICU
11. **Eye Surgeries:** Cataract Surgery, LASIK
12. **Dental Procedures:** Dental Filling, Root Canal, Orthodontics
13. **Others:** Dialysis, Physiotherapy, Vaccinations, Blood Tests

**Dataset Specifications:**

- **Size:** ~50 procedures with detailed cost information
- **Format:** CSV
- **Source:** Aggregated from hospital pricing data and healthcare surveys
- **File Location:** `backend/data/procedures_full_50.csv`

**Cost Range Examples:**

- Chest X-Ray: ₹200 - ₹1,500
- Normal Delivery: ₹30,000 - ₹70,000
- Kidney Transplant: ₹8,00,000 - ₹20,00,000
- Liver Transplant: ₹20,00,000 - ₹50,00,000

---

## D. Hospital Network Dataset

This dataset contains detailed information about hospitals across India, including their infrastructure and service capabilities.

| Feature                  | Description                                                                 |
| ------------------------ | --------------------------------------------------------------------------- |
| **Hospital ID**          | Unique identifier for each hospital (e.g., H200000)                         |
| **Name**                 | Official name of the healthcare facility                                    |
| **State**                | Indian state where hospital is located                                      |
| **City**                 | City of operation                                                           |
| **Pincode**              | Postal code for precise location                                            |
| **Bed Count**            | Total number of beds available                                              |
| **Specialties**          | List of medical specialties offered (Cardiology, Oncology, Neurology, etc.) |
| **Address**              | Full street address                                                         |
| **Latitude**             | Geographic latitude coordinate                                              |
| **Longitude**            | Geographic longitude coordinate                                             |
| **Is Empanelled Public** | Whether hospital is government-empanelled (yes/no)                          |
| **Created At**           | Date record was added to system                                             |

**Specialty Coverage:**

- General Medicine
- Cardiology
- Neurology
- Orthopedics
- Pediatrics
- Oncology
- Gastroenterology
- Nephrology
- ENT (Ear, Nose, Throat)

**Data Characteristics:**

- Enables location-based hospital recommendations
- Used for network coverage analysis
- Supports cashless claim facility mapping

**Dataset Specifications:**

- **Size:** ~1,000 hospital records
- **Format:** CSV
- **Source:** Public healthcare directories and hospital registrations
- **File Location:** `backend/data/hospitals_large.csv`

**Geographic Coverage:**

- **States Covered:** All major Indian states
- **Cities:** Major metros and tier-2 cities
- **Bed Capacity Range:** 46 - 1,182 beds

---

## E. Plan-Hospital Network Mapping Dataset

This dataset establishes the relationship between insurance plans and hospitals, defining network coverage and contract types.

| Feature            | Description                                               |
| ------------------ | --------------------------------------------------------- |
| **Plan ID**        | Reference to insurance plan                               |
| **Hospital ID**    | Reference to hospital facility                            |
| **Is In Network**  | Whether hospital is covered under plan (yes/no)           |
| **Contract Type**  | Type of arrangement (cashless, reimbursement, empanelled) |
| **Rank**           | Priority ranking of hospital within plan network          |
| **Distance Score** | Geographic proximity score                                |
| **Added On**       | Date when hospital was added to plan network              |

**Contract Types Explained:**

1. **Cashless:** Direct billing between hospital and insurer
2. **Reimbursement:** Patient pays first, claims later
3. **Empanelled:** Government-approved facility with special rates

**Data Characteristics:**

- Supports cashless facility finder
- Enables network adequacy analysis
- Used for claim processing validation

**Dataset Specifications:**

- **Size:** ~53,700 plan-hospital mappings
- **Format:** CSV
- **Source:** Insurance provider network data
- **File Location:** `backend/data/plan_hospital_map_large.csv`

**Network Statistics:**

- Average hospitals per plan: ~260
- Distance scores range: 2 km - 49 km

---

## F. User-Plan Interaction Dataset

This dataset tracks user interactions with insurance plans and claim events for training the recommendation system.

| Feature          | Description                                                       |
| ---------------- | ----------------------------------------------------------------- |
| **User ID**      | Reference to user profile                                         |
| **Plan ID**      | Reference to insurance plan                                       |
| **Event Type**   | Type of interaction (view, click, claim_approved, claim_rejected) |
| **Label**        | Binary label for recommendation training (0 or 1)                 |
| **Date**         | Timestamp of interaction                                          |
| **Claim Amount** | Amount claimed (if event is claim-related)                        |

**Event Types:**

1. **View:** User viewed plan details
2. **Click:** User clicked on plan for more information
3. **Claim Approved:** Insurance claim was approved
4. **Claim Rejected:** Insurance claim was rejected

**Data Characteristics:**

- Used for training collaborative filtering models
- Enables personalized recommendations based on user behavior
- Tracks claim approval patterns

**Dataset Specifications:**

- **Size:** ~10,000 interaction records
- **Format:** CSV
- **Source:** Simulated user behavior and claim history
- **File Location:** `backend/data/interactions.csv`

**Interaction Statistics:**

- Claim amounts range: ₹20,000 - ₹400,000
- Date range: 2024-2025
- Event distribution: Majority views, followed by clicks and claims

---

## G. Medical Bill Dataset

This dataset contains synthetic medical bill samples in text and image formats.
They were created to test and train the OCR module responsible for parsing uploaded medical bills.
Each bill includes:

| Field                     | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| **Bill ID**               | Unique identifier for each bill document             |
| **Patient Name**          | Randomly generated placeholder name (anonymized)     |
| **Hospital Name**         | Name of healthcare provider                          |
| **Date of Service**       | Bill issue date                                      |
| **Procedure / Diagnosis** | Medical procedure performed or diagnosis             |
| **Line Items**            | Individual charges (consultations, tests, medicines) |
| **Item Cost**             | Cost of each line item in INR                        |
| **Total Amount**          | Total bill amount in INR                             |
| **Covered Amount**        | Amount claimable under insurance                     |
| **Uncovered Amount**      | Out-of-pocket expense for patient                    |

**Bill Types Included:**

1. **Consultation Bills:** Doctor visit charges
2. **Diagnostic Bills:** X-rays, blood tests, imaging
3. **Medication Bills:** Pharmaceutical expenses
4. **Surgery Bills:** Procedure and hospitalization charges
5. **Emergency Bills:** Emergency room visits

**Data Characteristics:**

- Bills stored in both text (.txt) and image formats (PDF, PNG, JPG)
- Used to train and validate OCR extraction accuracy
- Includes varied formatting and layouts to test robustness

**Dataset Specifications:**

- **Size:** ~50+ synthetic bill samples
- **Formats:** TXT, PDF, PNG, JPG
- **Source:** Synthetically generated based on real bill templates
- **File Locations:**
  - `backend/data/bills_demo/` - Sample text bills
  - `backend/data/bill_scans/` - Scanned bill images
  - `uploads/` - User-uploaded bills for testing

**Sample Bill Content:**

```
X-ray chest          ₹340.00
Consultation         ₹120.00
Paracetamol          ₹20.00
--------------------------------
Total               ₹480.00
```

**OCR Module Applications:**

- Automatic bill amount extraction
- Procedure identification
- Hospital name recognition
- Date parsing
- Itemized cost breakdown

---

## Data Pipeline Summary

### Data Flow:

1. **User Input** → User Profile Dataset
2. **Plan Search** → Insurance Plan Dataset + Plan-Hospital Mapping
3. **Hospital Search** → Hospital Network Dataset
4. **Bill Upload** → Medical Bill Dataset (OCR Processing)
5. **Recommendations** → User-Plan Interaction Dataset + ML Models
6. **Cost Estimation** → Medical Procedures Dataset

### Data Quality Measures:

- **Completeness:** All critical fields populated
- **Consistency:** Standardized formats across datasets
- **Accuracy:** Validated against real-world data sources
- **Privacy:** User data anonymized and synthetic
- **Freshness:** Regular updates to pricing and network data

### Storage & Format:

- **Primary Format:** CSV for structured data
- **Text Files:** For bill samples
- **Database:** SQLite for user profiles and interactions
- **Encoding:** UTF-8 for multilingual support

---

## Dataset Usage in AI-MedPay Modules

| Module                         | Datasets Used                                       |
| ------------------------------ | --------------------------------------------------- |
| **Plan Recommendation Engine** | User Profile, Insurance Plan, User-Plan Interaction |
| **Hospital Finder**            | Hospital Network, Plan-Hospital Mapping             |
| **Bill Scanner (OCR)**         | Medical Bill Dataset                                |
| **Cost Estimator**             | Medical Procedures, Hospital Network                |
| **Chatbot**                    | All datasets for contextual responses               |
| **Claims Assistant**           | User Profile, Insurance Plan, Medical Procedures    |

---

## Data Augmentation & Preprocessing

### Techniques Applied:

1. **Normalization:** Numerical features scaled to 0-1 range
2. **Encoding:** Categorical variables converted to numerical representations
3. **Missing Value Handling:** Imputation using median/mode strategies
4. **Feature Engineering:** Derived features like risk scores, affordability index
5. **Synthetic Generation:** User interactions and bill samples expanded using templates

### Train-Test Split:

- **Training Set:** 70% of interaction data
- **Validation Set:** 15% of interaction data
- **Test Set:** 15% of interaction data

---

## Data Sources & Licensing

- **Government Data:** IRDAI (Insurance Regulatory and Development Authority of India)
- **Public Repositories:** Open healthcare datasets
- **Synthetic Data:** Generated for testing and privacy compliance
- **License:** Data used for educational and non-commercial purposes
- **Privacy Compliance:** GDPR and data protection standards followed

---

## Future Dataset Enhancements

1. **Expansion:** Add more regional hospitals and insurance plans
2. **Real-time Updates:** Integration with live insurance APIs
3. **Multilingual Bills:** Support for bills in regional languages
4. **Claim Outcomes:** Historical claim approval/rejection data
5. **User Feedback:** Incorporate actual user satisfaction ratings
6. **Medical Inflation:** Track year-over-year cost changes

---

_Last Updated: October 29, 2025_
