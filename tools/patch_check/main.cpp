// Applies a patch with Mesen's own IpsPatcher/UpsPatcher/BpsPatcher code and
// compares the result byte-for-byte with the expected ROM.
//
// Build (copy the patcher sources next to these two files first):
//   cp ../mesence/Utilities/Patches/{Ips,Ups,Bps}Patcher.{h,cpp} ../mesence/Utilities/CRC32.{h,cpp} .
//   g++ -std=c++17 -O2 -w -I. -o patch_check main.cpp IpsPatcher.cpp UpsPatcher.cpp BpsPatcher.cpp CRC32.cpp
//   ./patch_check <original.nes> <patch> <expected.nes>
// (pch.h is a stand-in for Mesen's Utilities/pch.h.)
#include "pch.h"
#include "IpsPatcher.h"
#include "UpsPatcher.h"
#include "BpsPatcher.h"

static vector<uint8_t> ReadAll(const char* path)
{
	std::ifstream f(path, std::ios::in | std::ios::binary);
	return vector<uint8_t>((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

int main(int argc, char** argv)
{
	if(argc != 4) {
		printf("usage: ips_check <original.nes> <patch> <expected.nes>\n");
		return 2;
	}

	vector<uint8_t> original = ReadAll(argv[1]);
	vector<uint8_t> patch = ReadAll(argv[2]);
	vector<uint8_t> expected = ReadAll(argv[3]);
	if(original.empty() || patch.empty() || expected.empty()) {
		printf("failed to read inputs\n");
		return 2;
	}

	// Same dispatch as VirtualFile::ApplyPatch
	vector<uint8_t> output;
	bool result = false;
	if(memcmp(patch.data(), "PATCH", 5) == 0) {
		printf("format: IPS\n");
		result = IpsPatcher::PatchBuffer(patch, original, output);
	} else if(memcmp(patch.data(), "UPS1", 4) == 0) {
		printf("format: UPS\n");
		result = UpsPatcher::PatchBuffer(string(argv[2]), original, output);
	} else if(memcmp(patch.data(), "BPS1", 4) == 0) {
		printf("format: BPS\n");
		result = BpsPatcher::PatchBuffer(string(argv[2]), original, output);
	} else {
		printf("format: unknown\n");
		return 1;
	}

	printf("patcher returned %s, output %zu bytes (expected %zu)\n", result ? "true" : "false", output.size(), expected.size());
	if(!result) {
		return 1;
	}
	if(output.size() != expected.size() || memcmp(output.data(), expected.data(), output.size()) != 0) {
		printf("MISMATCH\n");
		return 1;
	}
	printf("output matches expected ROM exactly\n");
	return 0;
}
