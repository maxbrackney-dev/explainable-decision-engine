#include "engine.h"
#include <cmath>
#include <sstream>

namespace engine {

std::string label_from_threshold(double prob, double threshold) {
    return (prob >= threshold) ? "high_risk" : "low_risk";
}

std::vector<std::string> ood_warnings(
    const std::unordered_map<std::string, double>& payload,
    const std::unordered_map<std::string, double>& means,
    const std::unordered_map<std::string, double>& stds,
    double z_threshold
) {
    std::vector<std::string> out;
    for (const auto& kv : payload) {
        const auto& key = kv.first;
        const double val = kv.second;

        auto mit = means.find(key);
        auto sit = stds.find(key);
        if (mit == means.end() || sit == stds.end()) continue;

        const double mu = mit->second;
        const double sd = sit->second;
        if (!std::isfinite(mu) || !std::isfinite(sd) || sd <= 1e-12) continue;

        const double z = (val - mu) / sd;
        if (std::fabs(z) >= z_threshold) {
            std::ostringstream ss;
            ss.setf(std::ios::fixed);
            ss.precision(2);
            ss << "ood_warning:" << key << ":z=" << z << " (threshold=" << z_threshold << ")";
            out.push_back(ss.str());
        }
    }
    return out;
}

} // namespace engine