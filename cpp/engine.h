#pragma once
#include <string>
#include <unordered_map>
#include <vector>

namespace engine {

std::string label_from_threshold(double prob, double threshold);

std::vector<std::string> ood_warnings(
    const std::unordered_map<std::string, double>& payload,
    const std::unordered_map<std::string, double>& means,
    const std::unordered_map<std::string, double>& stds,
    double z_threshold
);

} // namespace engine