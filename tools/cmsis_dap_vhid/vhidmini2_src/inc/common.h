/*++

Copyright (c) Microsoft Corporation.  All rights reserved.

    THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY
    KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR
    PURPOSE.

Module Name:

    common.h

Environment:

    User mode

--*/

#ifndef __VHIDMINI_COMMON_H__
#define __VHIDMINI_COMMON_H__

#define CMSIS_DAP_REPORT_ID                               0x00
#define CMSIS_DAP_REPORT_SIZE                             64

//
// Legacy control codes are retained for compatibility with the original
// sample but are not used by the CMSIS-DAP virtual probe.
//
#define  HIDMINI_CONTROL_CODE_SET_ATTRIBUTES              0x00
#define  HIDMINI_CONTROL_CODE_DUMMY1                      0x01
#define  HIDMINI_CONTROL_CODE_DUMMY2                      0x02

//
// Single report (ID 0). Kept for compatibility with existing sample logic.
//
#define CONTROL_COLLECTION_REPORT_ID                      CMSIS_DAP_REPORT_ID
#define TEST_COLLECTION_REPORT_ID                         0x02

#define MAXIMUM_STRING_LENGTH           (126 * sizeof(WCHAR))
#define VHIDMINI_MANUFACTURER_STRING    L"Virtual CMSIS-DAP Manufacturer"
#define VHIDMINI_PRODUCT_STRING         L"CMSIS-DAP Virtual Debug Probe"
#define VHIDMINI_SERIAL_NUMBER_STRING   L"CMSIS-DAP-0001"
#define VHIDMINI_DEVICE_STRING          L"CMSIS-DAP Virtual Device"
#define VHIDMINI_DEVICE_STRING_INDEX    5
#include <pshpack1.h>

typedef struct _MY_DEVICE_ATTRIBUTES {

    USHORT          VendorID;
    USHORT          ProductID;
    USHORT          VersionNumber;

} MY_DEVICE_ATTRIBUTES, *PMY_DEVICE_ATTRIBUTES;

typedef struct _HIDMINI_CONTROL_INFO {

    //
    //report ID of the collection to which the control request is sent
    //
    UCHAR    ReportId;   

    //
    // One byte control code (user-defined) for communication with hid 
    // mini driver
    //
    UCHAR   ControlCode;

    //
    // This union contains input data for the control request.
    //
    union {
        MY_DEVICE_ATTRIBUTES Attributes;
        struct {
            ULONG Dummy1;
            ULONG Dummy2;
        } Dummy;
    } u;
    
} HIDMINI_CONTROL_INFO, * PHIDMINI_CONTROL_INFO;

//
// CMSIS-DAP v1 reports are 64 bytes with no report ID.
//
typedef struct _HIDMINI_INPUT_REPORT {
    UCHAR Data[CMSIS_DAP_REPORT_SIZE];
} HIDMINI_INPUT_REPORT, *PHIDMINI_INPUT_REPORT;

typedef struct _HIDMINI_OUTPUT_REPORT {
    UCHAR Data[CMSIS_DAP_REPORT_SIZE];
} HIDMINI_OUTPUT_REPORT, *PHIDMINI_OUTPUT_REPORT;

#include <poppack.h>

//
// SetFeature request requires that the feature report buffer size be exactly 
// same as the size of report described in the hid report descriptor (
// excluding the report ID). Since HIDMINI_CONTROL_INFO includes report ID,
// we subtract one from the size.
//
#define FEATURE_REPORT_SIZE_CB      ((USHORT)(sizeof(HIDMINI_CONTROL_INFO) - 1))
#define INPUT_REPORT_SIZE_CB        ((USHORT)(sizeof(HIDMINI_INPUT_REPORT)))
#define OUTPUT_REPORT_SIZE_CB       ((USHORT)(sizeof(HIDMINI_OUTPUT_REPORT)))

#endif //__VHIDMINI_COMMON_H__
