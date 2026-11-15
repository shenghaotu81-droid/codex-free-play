// Transport only: this executable calls the pinned project's unmodified algorithms.
#include "vision/detection/detector.hpp"
#include "vision/pose/pose_estimator.hpp"
#include "vision/tracking/target_tracker.hpp"
#include <opencv2/calib3d.hpp>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char **argv) {
    try {
        if (argc != 10) throw std::runtime_error("config-dir width height focal k1 k2 p1 p2 k3 required");
        cv::setNumThreads(1);
        const std::filesystem::path config(argv[1]);
        const int width = std::stoi(argv[2]), height = std::stoi(argv[3]);
        const double focal = std::stod(argv[4]);
        auto pose_config = mark::pose::load_pose_config(config / "pose.yaml");
        pose_config.camera_.K_ = (cv::Mat_<double>(3,3) << focal,0,width/2.,0,focal,height/2.,0,0,1);
        pose_config.camera_.dist_ = cv::Mat::zeros(1,5,CV_64F);
        for (int i=0; i<5; ++i) pose_config.camera_.dist_.at<double>(0,i) = std::stod(argv[5+i]);
        pose_config.camera_.image_size_ = {width,height};
        mark::detector::Detector detector(mark::detector::load_detector_config(config / "detector.yaml"));
        mark::pose::PoseEstimator estimator(pose_config);
        mark::tracking::TargetTracker tracker(mark::tracking::load_tracking_config(config / "tracking.yaml"));
        cv::Mat image(height,width,CV_8UC3), rotation = cv::Mat::eye(3,3,CV_64F);
        uint64_t id;
        int64_t us;
        std::cout << std::setprecision(12);
        while (std::cin >> id >> us) {
            if (std::cin.get() != '\n') throw std::runtime_error("invalid image header");
            std::cin.read(reinterpret_cast<char*>(image.data), static_cast<std::streamsize>(image.total()*3));
            if (!std::cin) throw std::runtime_error("truncated image");
            mark::pose::CaptureStamp stamp;
            stamp.session_id_ = "exchange-sim";
            stamp.camera_id_ = pose_config.camera_.camera_id_;
            stamp.clock_domain_ = "simulation";
            stamp.pixel_domain_ = mark::pose::PixelDomain::RawDistorted;
            stamp.frame_id_ = id;
            stamp.received_us_ = us;
            stamp.exposure_us_ = us;
            auto detections = detector.process({image,id,us});
            mark::tracking::TrackingFrame input;
            input.stamp_ = stamp;
            for (size_t i=0; i<detections.detections_.size(); ++i) {
                auto obs = estimator.estimate_mark(detections,i,image.size(),stamp);
                if (obs.estimate_) cv::Rodrigues(obs.estimate_->pose_.rvec_,rotation);
                input.observations_.push_back(std::move(obs));
            }
            const auto result = tracker.step(input);
            if (result.tracks_.empty()) {
                std::cout << "{\"available\":false,\"detections\":" << detections.detections_.size() << "}" << std::endl;
                continue;
            }
            const auto &track = result.tracks_.front();
            const cv::Mat offset = rotation * (cv::Mat_<double>(3,1) << .04,.04,0.);
            const cv::Vec3d velocity = track.velocity_mps_.value_or(cv::Vec3d(0,0,0));
            std::cout << "{\"available\":true,\"x\":" << track.position_m_[0]+offset.at<double>(0)
                      << ",\"y\":" << track.position_m_[1]+offset.at<double>(1)
                      << ",\"depth\":" << track.position_m_[2]+offset.at<double>(2)
                      << ",\"vx\":" << velocity[0] << ",\"vy\":" << velocity[1] << ",\"vz\":" << velocity[2]
                      << ",\"measured\":" << (track.state_==mark::tracking::TrackState::Measured ? "true":"false")
                      << ",\"measurement_at\":" << track.last_measurement_stamp_.received_us_*1e-6
                      << ",\"detections\":" << detections.detections_.size() << "}" << std::endl;
        }
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "campus_bridge: " << e.what() << '\n';
        return 1;
    }
}
